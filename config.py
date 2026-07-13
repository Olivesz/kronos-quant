"""KRONOS configuration — every knob in one place."""
from dataclasses import dataclass, field

UNIVERSE = [
    # mega-caps across sectors
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
    "JPM", "BAC", "GS",
    "UNH", "JNJ", "PFE",
    "XOM", "CVX",
    "CAT", "HON", "BA",
    "WMT", "PG", "KO", "PEP", "MCD", "HD",
    "DIS", "NFLX", "CRM", "ADBE", "INTC", "CSCO", "ORCL",
    "T", "VZ", "NEE", "DUK", "LIN", "FDX", "UPS",
    # ETFs for diversification + pairs fodder
    "SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLK", "XLU",
    "GLD", "TLT", "HYG", "LQD",
]

MARKET_PROXY = "SPY"

REGIME_NAMES = {0: "Bull", 1: "Volatile", 2: "Bear"}

# strategy weights per regime: (momentum, mean_reversion, low_vol)
REGIME_STRATEGY_WEIGHTS = {
    "Bull":     {"momentum": 0.55, "mean_reversion": 0.15, "low_vol": 0.30},
    "Volatile": {"momentum": 0.20, "mean_reversion": 0.40, "low_vol": 0.40},
    "Bear":     {"momentum": 0.10, "mean_reversion": 0.30, "low_vol": 0.60},
}


@dataclass
class Config:
    seed: int = 42
    start: str = "2010-01-01"
    end: str = "2026-06-05"

    # data hygiene
    min_coverage: float = 0.95
    max_ffill_days: int = 3

    # HMM
    n_states: int = 3
    hmm_min_train: int = 750          # obs before first fit
    hmm_refit_every: int = 21         # trading days
    hmm_vol_window: int = 10
    hmm_max_iter: int = 200
    hmm_tol: float = 1e-6
    hmm_hysteresis_prob: float = 0.65
    hmm_hysteresis_days: int = 5
    hmm_min_dwell: int = 10           # min days in a regime before switching
    hmm_urgent_prob: float = 0.90     # ...unless the new state is near-certain

    # signals
    mom_lookback: int = 252
    mom_skip: int = 21
    rev_window: int = 20
    lowvol_window: int = 60
    signal_cap: float = 3.0

    # pairs
    pairs_formation: int = 252
    pairs_n: int = 8
    pairs_corr_min: float = 0.82
    pairs_adf_tstat: float = -3.0
    pairs_entry_z: float = 2.5
    pairs_exit_z: float = 0.75
    pairs_stop_z: float = 4.5
    pairs_max_hold: int = 60
    pairs_delta: float = 1e-5         # Kalman process-noise trick
    pairs_gross_sleeve: float = 0.10  # gross exposure of pairs overlay

    # covariance
    cov_window: int = 252
    cov_ewma_halflife: int = 63

    # Black-Litterman
    bl_delta: float = 2.5
    bl_tau: float = 0.05
    bl_view_lambda: float = 0.30      # signal tilts E[r] by up to lambda*sigma
    bl_tilt_kappa: float = 1.00
    max_weight: float = 0.12

    # risk
    vol_target: float = 0.13          # annualized
    cvar_alpha: float = 0.95
    cvar_target: float = 0.018        # daily CVaR95 target
    dd_start: float = -0.08
    dd_floor_at: float = -0.20
    dd_min_exposure: float = 0.25
    risk_smooth_days: int = 5

    # backtest
    rebalance_every: int = 21
    commission_bps: float = 1.0
    spread_bps: float = 2.0
    impact_coeff: float = 10.0        # impact_bps = c * sigma_d * sqrt(|dw|/1%)
    impact_cap_bps: float = 25.0
    no_trade_band: float = 0.0025

    universe: list = field(default_factory=lambda: list(UNIVERSE))
    market: str = MARKET_PROXY


CFG = Config()
