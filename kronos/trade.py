"""KRONOS-TRADE: a research-grounded, deployable trading system (DESIGN12).

The alpha comes from the FORECASTABLE channel (HAR volatility forecasting +
regime-gated risk parity), never from daily direction timing (which the BITS
study proved is a closed channel). Objective: risk-adjusted return, not CAGR.
Strictly causal and walk-forward throughout.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import REGIME_NAMES
from kronos.black_litterman import construct_portfolio
from kronos.covariance import shrunk_cov
from kronos.regime import walkforward_regimes
from kronos.signals import combined_signal
from kronos.volest import gk_variance
from kronos.vollab import HAR


@dataclass
class TradeConfig:
    rebalance: int = 21
    cov_window: int = 252
    cov_halflife: int = 63
    har_refit: int = 21
    har_min: int = 504
    vol_target: float = 0.11          # annualized portfolio vol target
    max_weight: float = 0.12
    no_trade_band: float = 0.0025
    dd_start: float = -0.08
    dd_floor_at: float = -0.20
    dd_min_exp: float = 0.25
    cvar_alpha: float = 0.95
    cvar_target: float = 0.018
    exp_smooth: int = 5
    commission_bps: float = 1.0
    spread_bps: float = 2.0
    forecast_vol: bool = True         # T1: forecast (HAR) vs realized targeting


class TradingSystem:
    def __init__(self, cfg: TradeConfig | None = None, base_cfg=None):
        self.cfg = cfg or TradeConfig()
        from config import CFG
        self.base = base_cfg or CFG

    # ------------------------------------------------------------ vol engine
    def _har_forecasts(self, gkvar: pd.DataFrame) -> pd.DataFrame:
        """Per-asset HAR 1-step annualized vol forecast, refit every har_refit,
        strictly causal (forecast at t uses data <= t)."""
        c = self.cfg
        dates = gkvar.index
        T = len(dates)
        out = pd.DataFrame(np.nan, index=dates, columns=gkvar.columns)
        for col in gkvar.columns:
            v = gkvar[col].to_numpy()
            fc = np.full(T, np.nan)
            model = None
            t = c.har_min
            while t < T:
                rv = v[:t]
                rv = rv[np.isfinite(rv)]
                if len(rv) > c.har_min // 2:
                    model = HAR().fit(rv)
                t_next = min(t + c.har_refit, T)
                if model is not None:
                    for s in range(t, t_next):
                        hist = v[:s][np.isfinite(v[:s])]
                        fc[s] = model.forecast_next(hist)
                t = t_next
            out[col] = np.sqrt(np.clip(fc, 1e-12, None) * 252)   # annualized vol
        return out

    # ---------------------------------------------------------------- engine
    def backtest(self, px: pd.DataFrame, ohlc: dict) -> dict:
        c = self.cfg
        rets = px.pct_change().fillna(0.0)
        gkv = gk_variance(ohlc["open"], ohlc["high"], ohlc["low"], ohlc["close"])
        gkv = gkv.reindex(px.index).reindex(columns=px.columns)
        dates = px.index
        n = len(dates)

        mkt = px[self.base.market].pct_change().dropna()
        regime = walkforward_regimes(mkt, self.base)["regime"].reindex(dates).ffill()
        har_vol = self._har_forecasts(gkv)        # annualized per-asset forecast
        realized_vol = (np.sqrt(gkv) * np.sqrt(252)).rolling(21).mean()

        warmup = max(c.cov_window + 5, self.base.hmm_min_train + 12, c.har_min + 22)
        rebal = list(range(warmup, n, c.rebalance))

        weights = pd.DataFrame(0.0, index=dates, columns=px.columns)
        target_log, sw_log = {}, {}
        current = pd.Series(0.0, index=px.columns)
        costs = np.zeros(n)
        daily_vol_for_cost = rets.rolling(60).std()

        for i in rebal:
            t = dates[i]
            reg = int(regime.iloc[i]) if np.isfinite(regime.iloc[i]) else 1
            reg = max(reg, 0)
            combo = combined_signal(px, t, reg, self.base)
            cov = shrunk_cov(rets.loc[:t].iloc[-c.cov_window:], c.cov_halflife, c.cov_window)
            port = construct_portfolio(cov, combo["combined"], self.base)
            target = port["weights"]
            dw = target - current
            dw[dw.abs() < c.no_trade_band] = 0.0
            new = (current + dw).clip(lower=0.0)
            if new.sum() > 0:
                new /= new.sum()
            if i + 1 < n:
                adw = (new - current).abs()
                tc = float((adw * (c.commission_bps + c.spread_bps) / 1e4).sum())
                costs[i + 1] += tc
            current = new
            target_log[t] = target
            sw_log[t] = {"regime": REGIME_NAMES.get(reg, "?"), **combo["weights"]}
            j_end = min(i + c.rebalance, n - 1)
            for j in range(i + 1, j_end + 1):
                weights.iloc[j] = current
                drifted = current * (1 + rets.iloc[j])
                s = drifted.sum()
                if s > 0:
                    current = drifted / s

        gross = (weights * rets).sum(axis=1)
        gross.iloc[:warmup + 1] = 0.0

        # ---- forecast-vol vs realized-vol targeting --------------------------
        vol_src = har_vol if c.forecast_vol else realized_vol
        # forecast portfolio vol = sqrt(w' D R D w), D=diag(per-asset vol fc),
        # R = recent return correlation (causal)
        corr = rets.rolling(c.cov_window).corr()       # causal rolling corr
        fc_pvol = np.full(n, np.nan)
        for i in range(warmup, n):
            w = weights.iloc[i].to_numpy()
            if w.sum() <= 0:
                continue
            d = vol_src.iloc[i - 1].to_numpy()          # known at i-1
            ok = np.isfinite(d) & (w > 0)
            if ok.sum() < 2:
                continue
            wv = w[ok]; dv = d[ok]
            try:
                R = rets.iloc[max(0, i - c.cov_window):i].iloc[:, ok].corr().to_numpy()
                R = np.nan_to_num(R, nan=0.0)
                np.fill_diagonal(R, 1.0)
            except Exception:
                R = np.eye(ok.sum())
            cov_f = (dv[:, None] * dv[None, :]) * R
            fc_pvol[i] = float(np.sqrt(max(wv @ cov_f @ wv, 1e-12)))
        fc_pvol_s = pd.Series(fc_pvol, index=dates).ffill()

        m_vol = (c.vol_target / fc_pvol_s).clip(upper=1.0).fillna(1.0)

        # mechanical crash control: CVaR cap + drawdown throttle on gross book
        def hist_cvar(x):
            q = np.quantile(x, 1 - c.cvar_alpha)
            tail = x[x <= q]
            return -tail.mean() if len(tail) else 0.0
        cvar = gross.rolling(252).apply(lambda x: hist_cvar(x.to_numpy()), raw=False)
        m_cvar = (c.cvar_target / cvar.replace(0, np.nan)).clip(upper=1.0).fillna(1.0)
        nav_g = (1 + gross).cumprod()
        dd = nav_g / nav_g.cummax() - 1.0
        span = c.dd_floor_at - c.dd_start
        m_dd = (1.0 + (dd - c.dd_start) * (1 - c.dd_min_exp) / span).clip(c.dd_min_exp, 1.0)

        exposure = pd.concat([m_vol, m_cvar, m_dd], axis=1).min(axis=1)
        exposure = exposure.ewm(span=c.exp_smooth).mean().clip(0.0, 1.0)
        exp_lag = exposure.shift(1).fillna(1.0)
        net = gross * exp_lag - costs

        start = dates[warmup]
        return {"net": net, "gross": gross, "weights": weights,
                "exposure": exposure, "exp_lag": exp_lag,
                "fc_pvol": fc_pvol_s, "costs": pd.Series(costs, index=dates),
                "targets": target_log, "sw_log": sw_log,
                "regime": regime, "har_vol": har_vol, "start": start,
                "warmup": warmup}

    # ------------------------------------------------------- recommendation
    def recommend(self, px: pd.DataFrame, ohlc: dict, notional: float = 100_000) -> dict:
        bt = self.backtest(px, ohlc)
        last = px.index[-1]
        # latest target portfolio (the most recent rebalance) scaled by exposure
        tdates = sorted(bt["targets"])
        tw = bt["targets"][tdates[-1]]
        tw = tw[tw > 0.005].sort_values(ascending=False)
        expo = float(bt["exposure"].iloc[-1])
        reg = int(bt["regime"].iloc[-1]) if np.isfinite(bt["regime"].iloc[-1]) else 1
        fcvol = float(bt["fc_pvol"].iloc[-1])    # already annualized portfolio vol
        alloc = (tw * expo * notional).round(0)
        cash = notional - float(alloc.sum())
        return {"as_of": str(last.date()), "regime": REGIME_NAMES.get(max(reg, 0), "?"),
                "forecast_portfolio_vol_ann": fcvol, "exposure": expo,
                "target_weights": {k: round(float(v), 4) for k, v in tw.items()},
                "dollar_alloc": {k: float(v) for k, v in alloc.items()},
                "cash": cash, "notional": notional,
                "rebalanced_on": str(tdates[-1].date())}
