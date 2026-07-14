"""Dashboard renderer: payload dict -> single self-contained HTML file.

No CDN, no server, no dependencies: a hand-written canvas charting engine
(crosshair tooltips, drag-zoom, log toggle, regime underlays, heatmaps)
embedded with the data as one JSON blob.
"""
from __future__ import annotations

import json


def render_dashboard(payload: dict, path: str) -> None:
    html = TEMPLATE.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")))
    with open(path, "w") as f:
        f.write(html)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KRONOS — Regime-Aware Quant Alpha Platform</title>
<style>
:root{
  --bg:#070b14; --panel:#0e1525; --panel2:#111a2e; --line:#1c2940;
  --txt:#d7e2f0; --dim:#7d8ca3; --faint:#46546b;
  --cyan:#27d3ee; --amber:#fbbf24; --rose:#fb7185; --green:#34d399;
  --violet:#a78bfa; --blue:#60a5fa; --orange:#fb923c;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);
  font:14px/1.45 -apple-system,"SF Pro Text","Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased}
.mono{font-family:"SF Mono",ui-monospace,Menlo,monospace}
.wrap{max-width:1340px;margin:0 auto;padding:22px 26px 60px}
header{display:flex;align-items:baseline;gap:18px;flex-wrap:wrap;
  padding:6px 2px 18px;border-bottom:1px solid var(--line);margin-bottom:20px}
.logo{font-size:30px;font-weight:800;letter-spacing:6px;
  background:linear-gradient(90deg,var(--cyan),var(--violet));
  -webkit-background-clip:text;background-clip:text;color:transparent}
.logo small{font-size:11px;letter-spacing:2px;color:var(--dim);
  -webkit-text-fill-color:var(--dim);display:block;margin-top:2px}
.badge{font-size:11px;letter-spacing:1px;padding:4px 10px;border-radius:20px;
  border:1px solid var(--line);color:var(--dim)}
.badge.live{color:var(--green);border-color:#1d4a3a}
.badge.regime-Bull{color:var(--green);border-color:#1d4a3a}
.badge.regime-Volatile{color:var(--amber);border-color:#4a3f1d}
.badge.regime-Bear{color:var(--rose);border-color:#4a1d2a}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:12px;margin-bottom:20px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:14px 16px 30px;position:relative;overflow:hidden}
.card .k{font-size:10.5px;letter-spacing:1.5px;color:var(--dim);text-transform:uppercase}
.card .v{font-size:24px;font-weight:700;margin-top:4px}
.card .s{font-size:11px;color:var(--faint);margin-top:1px;position:relative;z-index:2}
.card canvas{position:absolute;right:0;bottom:0;left:0;height:22px;width:100%;opacity:.32}
.pos{color:var(--green)}.neg{color:var(--rose)}.neu{color:var(--cyan)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:18px 20px;margin-bottom:18px}
.panel h2{font-size:13px;letter-spacing:2px;color:var(--dim);text-transform:uppercase;
  margin-bottom:4px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.panel .sub{font-size:12px;color:var(--faint);margin-bottom:12px}
.row{display:grid;gap:18px}
.row.c2{grid-template-columns:3fr 2fr}
.row.c2e{grid-template-columns:1fr 1fr}
@media(max-width:980px){.row.c2,.row.c2e{grid-template-columns:1fr}}
.chart{position:relative;width:100%}
.chart canvas{display:block;width:100%;cursor:crosshair}
.tip{position:absolute;pointer-events:none;background:#0a1120ee;border:1px solid var(--line);
  border-radius:8px;padding:8px 11px;font-size:11.5px;display:none;z-index:10;
  box-shadow:0 6px 24px #0009;min-width:130px}
.tip .d{color:var(--dim);margin-bottom:4px;font-size:10.5px;letter-spacing:.5px}
.tip .r{display:flex;justify-content:space-between;gap:14px}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:var(--dim);
  margin-left:auto}
.legend span{cursor:pointer;display:inline-flex;align-items:center;gap:5px;user-select:none}
.legend span.off{opacity:.32}
.legend i{width:14px;height:3px;border-radius:2px;display:inline-block}
.btn{cursor:pointer;font-size:10.5px;letter-spacing:1px;color:var(--dim);
  border:1px solid var(--line);border-radius:6px;padding:3px 9px;user-select:none}
.btn.on{color:var(--cyan);border-color:#1b4a56}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{font-size:10.5px;letter-spacing:1.2px;color:var(--dim);text-transform:uppercase;
  text-align:right;padding:7px 10px;border-bottom:1px solid var(--line)}
td{padding:7px 10px;text-align:right;border-bottom:1px solid #14203522}
th:first-child,td:first-child{text-align:left}
.gtable td{font-family:"SF Mono",ui-monospace,Menlo,monospace;font-size:12px}
footer{color:var(--faint);font-size:11.5px;line-height:1.7;margin-top:26px;
  border-top:1px solid var(--line);padding-top:14px}
.greeks{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}
.greek{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.greek .g{font-size:20px;font-weight:700}
.greek .k{font-size:10px;letter-spacing:1.5px;color:var(--dim);text-transform:uppercase}
.greek .s{font-size:10.5px;color:var(--faint);margin-top:3px}
.tabs{display:flex;gap:8px;margin:0 0 20px}
.tab{cursor:pointer;font-size:12px;letter-spacing:2px;padding:8px 22px;
  border:1px solid var(--line);border-radius:10px;color:var(--dim);user-select:none}
.tab.on{color:var(--cyan);border-color:#1b4a56;background:#0c1a26}
.qgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));
  gap:14px;margin-bottom:18px}
.qcard{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px}
.qcard .qq{font-size:10.5px;letter-spacing:1.5px;color:var(--dim);text-transform:uppercase}
.qcard .qa{font-size:15px;font-weight:600;margin:6px 0 4px}
.qcard .qd{font-size:12px;color:var(--dim);line-height:1.5}
.verdict-yes{color:var(--green)} .verdict-no{color:var(--rose)}
.verdict-mixed{color:var(--amber)}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="logo">KRONOS<small>REGIME-AWARE QUANT ALPHA PLATFORM</small></div>
    <span class="badge live" id="b-src"></span>
    <span class="badge" id="b-range"></span>
    <span class="badge" id="b-uni"></span>
    <span class="badge" id="b-regime"></span>
  </header>

  <div class="tabs" id="tabbar" style="display:none">
    <div class="tab on" data-tab="overview">OVERVIEW</div>
    <div class="tab" data-tab="research">RESEARCH</div>
  </div>

  <div id="tab-overview">
  <div class="cards" id="cards"></div>

  <div class="panel">
    <h2>Equity Curve <span class="btn" id="logbtn">LOG</span>
      <span class="sub" style="margin:0">drag to zoom · double-click to reset · regime bands underlay</span>
      <span class="legend" id="lg-eq"></span></h2>
    <div class="chart" id="ch-eq"></div>
    <div class="chart" id="ch-dd" style="margin-top:6px"></div>
  </div>

  <div class="row c2">
    <div class="panel">
      <h2>Regime Engine — Filtered Probabilities <span class="legend" id="lg-rg"></span></h2>
      <div class="sub">Walk-forward Gaussian HMM (causal: only data ≤ t). Hysteresis-stabilized.</div>
      <div class="chart" id="ch-rg"></div>
    </div>
    <div class="panel">
      <h2>Transition Matrix &amp; Per-Regime Performance</h2>
      <div class="sub">Estimated daily transition probabilities (final fit)</div>
      <div class="chart" id="ch-tm" style="max-width:280px"></div>
      <table class="gtable" id="tbl-regime" style="margin-top:12px"></table>
    </div>
  </div>

  <div class="row c2">
    <div class="panel">
      <h2>Strategy Attribution — Stand-alone Sleeve NAVs <span class="legend" id="lg-sl"></span></h2>
      <div class="sub">Each sleeve run through the identical HRP+BL pipeline in isolation, net of costs</div>
      <div class="chart" id="ch-sl"></div>
    </div>
    <div class="panel">
      <h2>Regime-Gated Strategy Allocation</h2>
      <div class="sub">Signal blend weights chosen by the prevailing regime at each rebalance</div>
      <div class="chart" id="ch-sw"></div>
    </div>
  </div>

  <div class="row c2">
    <div class="panel">
      <h2>Current Portfolio — HRP backbone × Black-Litterman tilt</h2>
      <div class="sub" id="sub-port"></div>
      <div class="chart" id="ch-w"></div>
    </div>
    <div class="panel">
      <h2>Weight History (top 25 by avg weight, monthly)</h2>
      <div class="chart" id="ch-wh"></div>
    </div>
  </div>

  <div class="panel">
    <h2>Risk Engine <span class="legend" id="lg-rk"></span></h2>
    <div class="sub">Exposure = smoothed min(vol-target, CVaR-target, drawdown throttle), applied T+1, no leverage</div>
    <div class="chart" id="ch-rk"></div>
    <div class="row c2e" style="margin-top:14px">
      <div>
        <h2 style="margin-bottom:8px">Realized Vol vs Target</h2>
        <div class="chart" id="ch-vol"></div>
      </div>
      <div>
        <h2 style="margin-bottom:8px">Daily Return Distribution</h2>
        <div class="chart" id="ch-hist"></div>
      </div>
    </div>
  </div>

  <div class="row c2">
    <div class="panel">
      <h2>Portfolio Greeks <span class="sub" style="margin:0">(factor sensitivities, trailing 1y)</span></h2>
      <div class="greeks" id="greeks"></div>
      <h2 style="margin:16px 0 8px">Rolling 60d Beta to SPY</h2>
      <div class="chart" id="ch-beta"></div>
    </div>
    <div class="panel">
      <h2>Kalman Pairs Sleeve</h2>
      <div class="sub" id="sub-pairs"></div>
      <div class="chart" id="ch-z"></div>
      <table id="tbl-pairs" style="margin-top:10px"></table>
    </div>
  </div>

  <div class="panel">
    <h2>Monthly Returns — KRONOS net</h2>
    <div class="chart" id="ch-mo"></div>
  </div>
  </div><!-- /tab-overview -->

  <div id="tab-research" style="display:none">
    <div class="qgrid" id="qcards"></div>

    <div class="panel">
      <h2>Q1 &amp; Q2 — Regime Model Horse Race</h2>
      <div class="sub">Walk-forward one-step predictive log-density of returns (eval 2019+), identical features &amp; protocol. Pre-registered decision rule.</div>
      <table class="gtable" id="tbl-race"></table>
      <div class="row c2e" style="margin-top:14px">
        <div><h2 style="margin-bottom:6px">How many regimes? (log-score vs K)</h2>
          <div class="chart" id="ch-ksweep"></div></div>
        <div><h2 style="margin-bottom:6px">Crash-detection latency (days)</h2>
          <table class="gtable" id="tbl-latency"></table></div>
      </div>
    </div>

    <div class="row c2">
      <div class="panel">
        <h2>Q3a — Volatility Forecasting Lab</h2>
        <div class="sub" id="sub-vollab"></div>
        <table class="gtable" id="tbl-vollab"></table>
        <div class="chart" id="ch-volfc" style="margin-top:12px"></div>
      </div>
      <div class="panel">
        <h2>Q3b — Is Volatility Rough?</h2>
        <div class="sub" id="sub-rough"></div>
        <div class="chart" id="ch-rough"></div>
        <div class="sub" id="sub-rough2" style="margin-top:8px"></div>
      </div>
    </div>

    <div class="row c2">
      <div class="panel">
        <h2>Q5a — Eigenvalue Spectrum &amp; Marchenko-Pastur</h2>
        <div class="sub" id="sub-rmt"></div>
        <div class="chart" id="ch-mp"></div>
        <table class="gtable" id="tbl-rmt" style="margin-top:10px"></table>
      </div>
      <div class="panel">
        <h2>Q5b — Min-CVaR LP vs HRP</h2>
        <div class="sub">Rockafellar-Uryasev linear program, walk-forward, net of costs</div>
        <table class="gtable" id="tbl-cvar"></table>
        <h2 style="margin:16px 0 6px">Eigenportfolio Stat-Arb (replaces Kalman pairs)</h2>
        <div class="sub" id="sub-statarb"></div>
        <div class="chart" id="ch-statarb"></div>
      </div>
    </div>

    <div class="panel">
      <h2>Q4 — Online Learning vs Hand-Made Regime Gates</h2>
      <div class="sub" id="sub-ens"></div>
      <div class="row c2e">
        <div><h2 style="margin-bottom:6px">Fixed-share expert weights</h2>
          <div class="chart" id="ch-river"></div></div>
        <div><h2 style="margin-bottom:6px">Cumulative regret vs best sleeve in hindsight</h2>
          <div class="chart" id="ch-regret"></div></div>
      </div>
      <table class="gtable" id="tbl-ens" style="margin-top:10px"></table>
    </div>

    <div class="panel">
      <h2>Q6 — Overfitting Forensics</h2>
      <div class="sub" id="sub-forensics"></div>
      <div class="row c2e">
        <div>
          <div class="greeks" id="forensic-cards"></div>
          <h2 style="margin:14px 0 6px">PBO: OOS-rank logits of IS winners</h2>
          <div class="chart" id="ch-pbo"></div>
        </div>
        <div><h2 style="margin-bottom:6px">Bootstrap equity fan (stationary, block≈3mo)</h2>
          <div class="chart" id="ch-fan"></div></div>
      </div>
    </div>

    <div class="panel" id="panel-tails" style="display:none">
      <h2>X² — Regimes or Fat Tails? (pre-registered mechanism study)</h2>
      <div class="sub">Control model: Student-t HMM (ECM, per-state ν). If extra Gaussian states were buying tail-fit, the t-HMM should peak at lower K.</div>
      <div class="row c2e">
        <div>
          <h2 style="margin-bottom:6px">Monte Carlo: chosen K on worlds with true K=3</h2>
          <table class="gtable" id="tbl-mc"></table>
          <div class="sub" id="sub-mc" style="margin-top:8px"></div>
        </div>
        <div>
          <h2 style="margin-bottom:6px">Real data: walk-forward log-score vs K</h2>
          <div class="chart" id="ch-tcurve"></div>
        </div>
      </div>
      <div class="row c2e" style="margin-top:14px">
        <div>
          <h2 style="margin-bottom:6px">Amisano-Giacomini tests (eval 2019+)</h2>
          <table class="gtable" id="tbl-ag"></table>
        </div>
        <div>
          <h2 style="margin-bottom:6px">Regime-model confidence set (α=10%)</h2>
          <table class="gtable" id="tbl-mcs"></table>
          <div class="sub" id="sub-nus" style="margin-top:8px"></div>
        </div>
      </div>
    </div>

    <div class="panel" id="panel-rfsv" style="display:none">
      <h2>X² — Does Roughness Forecast? (RFSV vs HAR)</h2>
      <div class="sub" id="sub-rfsv"></div>
      <table class="gtable" id="tbl-rfsv"></table>
    </div>

    <div class="panel" id="panel-laws" style="display:none">
      <h2>LAWS — The One-Clock Hypothesis &amp; Friends (pre-registered invariance screens)</h2>
      <div class="sub">Hypothesis: the volatility path is the only clock — returns are conditionally Gaussian given it; regimes, fat tails, and hallucinated HMM states are the vol path in costume.</div>
      <div class="row c2e">
        <div>
          <h2 style="margin-bottom:6px">L1 — Deformation kills the tails (48 assets)</h2>
          <div class="chart" id="ch-l1"></div>
          <div class="sub" id="sub-l1" style="margin-top:6px"></div>
        </div>
        <div>
          <h2 style="margin-bottom:6px">P1b — ...and the hallucinated regimes die with them</h2>
          <table class="gtable" id="tbl-p1b"></table>
          <h2 style="margin:12px 0 6px">L2 / L3 verdicts</h2>
          <table class="gtable" id="tbl-l23"></table>
        </div>
      </div>
    </div>

    <div class="panel" id="panel-clock" style="display:none">
      <h2>CLOCK — Is Systemic Risk Just Correlated Clocks?</h2>
      <div class="sub">All 1,128 pairs vs finite-sample Gaussian-copula nulls (rank-calibrated). Same-day deformation tests the copula GIVEN the clocks; lagged deformation tests for common surprises beyond yesterday's information.</div>
      <div class="chart" id="ch-clock"></div>
      <table class="gtable" id="tbl-clock" style="margin-top:12px"></table>
      <div class="sub" id="sub-clock" style="margin-top:8px"></div>
    </div>

    <div class="panel" id="panel-surge" style="display:none">
      <h2>SURGE — The Structure of Common Volatility Surprises</h2>
      <div class="sub">Interrogating CLOCK's irreducible object: the clock surges themselves. Cascade recursion, the arrow of time, and an audit of our own "unpredictable" verdict.</div>
      <div class="row c2e">
        <div>
          <h2 style="margin-bottom:6px">Leverage kernels L(τ) = corr(r_t, v_{t+τ})</h2>
          <div class="chart" id="ch-lev"></div>
        </div>
        <div>
          <h2 style="margin-bottom:6px">Verdicts</h2>
          <table class="gtable" id="tbl-surge"></table>
        </div>
      </div>
    </div>

    <div class="panel" id="panel-bits" style="display:none">
      <h2>BITS — The Information Budget of the Market</h2>
      <div class="sub">How many bits/day does the past leak about the future — and what Sharpe could ANY strategy achieve? Kelly: max log-growth edge = mutual information. Estimators gated against closed-form Gaussian/AR truth (X17).</div>
      <div class="row c2e">
        <div>
          <h2 style="margin-bottom:6px">The budget table</h2>
          <table class="gtable" id="tbl-bits"></table>
        </div>
        <div>
          <h2 style="margin-bottom:6px">Ceilings &amp; utilization</h2>
          <table class="gtable" id="tbl-ceil"></table>
          <div class="sub" id="sub-bits" style="margin-top:8px"></div>
        </div>
      </div>
    </div>

    <div class="panel" id="panel-decathlon" style="display:none">
      <h2>DECATHLON — The Minimal Market vs the Ten-Event Battery</h2>
      <div class="sub">A minimal agent-based market (aggregated flows, frozen parameters) ablated ingredient by ingredient and scored on the battery our research validated. SPY scores 10/10, GBM 3/10 by calibration (gate X19).</div>
      <table class="gtable" id="tbl-deca"></table>
      <div class="sub" id="sub-deca" style="margin-top:10px"></div>
    </div>

    <div class="panel" id="panel-critical" style="display:none">
      <h2>CRITICAL — Are Crashes Critical Transitions or Shocks?</h2>
      <div class="sub">Do critical-slowing-down early-warnings predict crashes BEYOND the volatility level (the confound that breaks naive EWS studies)? Incremental walk-forward AUC, embargoed, vs a synthetic fold/shock gate that proves the test convicts and exonerates.</div>
      <div class="row c2e">
        <div>
          <h2 style="margin-bottom:6px">Pre-crash precursor (std units): real vs a known bifurcation</h2>
          <div class="chart" id="ch-precursor"></div>
          <div class="sub" id="sub-crit2" style="margin-top:6px"></div>
        </div>
        <div>
          <h2 style="margin-bottom:6px">The verdict &amp; its anchor</h2>
          <table class="gtable" id="tbl-critical"></table>
          <div class="sub" id="sub-crit" style="margin-top:8px"></div>
        </div>
      </div>
    </div>

    <div class="panel" id="panel-reflex" style="display:none">
      <h2>REFLEX — How Endogenous Is the Market?</h2>
      <div class="sub">Hawkes branching ratio n = fraction of extreme events that are aftershocks. Decomposed by volatility deformation: raw events (clustering + jumps) vs vol-clock-adjusted events (genuine reflexivity). Estimator recovery-curve-debiased; gate X21.</div>
      <div class="row c2e">
        <div>
          <h2 style="margin-bottom:6px">Branching ratio: raw vs deformed vs no-self-excitation null</h2>
          <div class="chart" id="ch-reflex"></div>
          <div class="sub" id="sub-reflex2" style="margin-top:6px"></div>
        </div>
        <div>
          <h2 style="margin-bottom:6px">The decomposition</h2>
          <table class="gtable" id="tbl-reflex"></table>
        </div>
      </div>
    </div>

    <div class="panel" id="panel-constants" style="display:none">
      <h2>CONSTANTS — Which Market Laws Are Actually Constant?</h2>
      <div class="sub">Every law KRONOS measured, estimated across 5 era-windows and classified CONSTANT / REGIME-VARYING / DRIFTING by a variance-ratio + bootstrapped-trend test (gate X22: 8% false-drift rate, 100% real-drift detection). The Adaptive-Markets question, answered.</div>
      <table class="gtable" id="tbl-constants"></table>
      <div class="sub" id="sub-constants" style="margin-top:10px"></div>
    </div>

    <div class="panel" id="panel-trade" style="display:none">
      <h2>TRADE — The Research-Grounded Trading System</h2>
      <div class="sub">The deployable system the findings license: alpha from the FORECASTABLE channel (HAR vol forecasting + regime-gated risk parity), never daily direction timing (BITS proved it's closed). Objective: risk-adjusted return. Gate X23: causal, and forecast-vol targeting beats realized when vol is forecastable.</div>
      <div class="chart" id="ch-trade"></div>
      <div class="row c2e" style="margin-top:12px">
        <div><h2 style="margin-bottom:6px">Backtest (net of costs)</h2>
          <table class="gtable" id="tbl-trade"></table></div>
        <div><h2 style="margin-bottom:6px">Today's portfolio (live recommendation)</h2>
          <table class="gtable" id="tbl-rec"></table>
          <div class="sub" id="sub-rec" style="margin-top:6px"></div></div>
      </div>
    </div>

    <div class="panel" id="panel-transfer" style="display:none">
      <h2>TRANSFER — Does Market Structure Cross Borders?</h2>
      <div class="sub" id="sub-transfer-head">Every law was measured on ONE universe (48 US tickers). Re-estimated on Japan, Europe and Asia-EM (locally-listed large caps, own timezone block each), then the CONSTANTS variance-ratio machinery run across SPACE. Second test: the frozen US-tuned trading system, ZERO re-tuning, on each foreign market. Gate X24.</div>
      <div class="row c2e">
        <div><h2 style="margin-bottom:6px">The 7-law battery across markets</h2>
          <table class="gtable" id="tbl-transfer-laws"></table>
          <div class="sub" id="sub-transfer-laws" style="margin-top:8px"></div></div>
        <div><h2 style="margin-bottom:6px">Frozen system vs local index (net of costs)</h2>
          <table class="gtable" id="tbl-transfer-frozen"></table>
          <div class="sub" id="sub-transfer-frozen" style="margin-top:8px"></div></div>
      </div>
    </div>

    <div class="panel" id="panel-crypto" style="display:none">
      <h2>CRYPTO — Do the Mechanism Laws Survive Outside Equities?</h2>
      <div class="sub" id="sub-crypto-head">The sharpest stress test: crypto breaks four equity assumptions at once — 24/7 (no overnight gap), retail-momentum flow, no financial leverage, no close auction. The same 7-law battery, run on 10 majors and placed beside the equity cohort. The differentiating prediction (C2): the leverage effect may INVERT. Gate X26 licenses the sign reading.</div>
      <div class="row c2e">
        <div><h2 style="margin-bottom:6px">The battery: crypto vs the equity cohort</h2>
          <table class="gtable" id="tbl-crypto-laws"></table>
          <div class="sub" id="sub-crypto-laws" style="margin-top:8px"></div></div>
        <div><h2 style="margin-bottom:6px">The leverage effect flips sign</h2>
          <div class="chart" id="ch-crypto-lev"></div>
          <table class="gtable" id="tbl-crypto-hyp" style="margin-top:10px"></table></div>
      </div>
    </div>

    <div class="panel">
      <h2>Synthesis — Did the science move the needle?</h2>
      <div class="sub">Identical core engine; overlays differ. Honest answer below.</div>
      <div class="chart" id="ch-synth"></div>
      <table class="gtable" id="tbl-synth" style="margin-top:10px"></table>
    </div>
  </div><!-- /tab-research -->

  <footer>
    <b>Honest fine print.</b> Backtest, not live trading. Universe is today's liquid mega-caps/ETFs
    (survivorship bias inflates results). Adjusted closes, T+1 execution, costs = 1bp commission +
    2bp spread + square-root impact (capped 25bp). Risk-free rate ≈ 0 in ratios. HMM probabilities
    used for decisions are strictly filtered (causal); models are refit walk-forward with no
    look-ahead. Past performance, simulated or otherwise, does not predict future returns.
    Generated <span id="f-gen"></span> · KRONOS v1.0
  </footer>
</div>

<script>
const DATA = __PAYLOAD__;
/* ============================ tiny chart engine ============================ */
const COL = {cyan:'#27d3ee',amber:'#fbbf24',rose:'#fb7185',green:'#34d399',
             violet:'#a78bfa',blue:'#60a5fa',orange:'#fb923c',dim:'#7d8ca3'};
const REGCOL = ['#34d39922','#fbbf2426','#fb718524'];
const REGSOLID = [COL.green,COL.amber,COL.rose];
const ts = s => Date.parse(s);
const fmt = {
  pct: v => (v*100).toFixed(1)+'%',
  pct2: v => (v*100).toFixed(2)+'%',
  nav: v => v.toFixed(2)+'×',
  num: v => v.toFixed(2),
  z: v => v.toFixed(2)+'σ',
};
function niceTicks(lo,hi,n=5){
  const span=hi-lo||1, step0=span/n, mag=Math.pow(10,Math.floor(Math.log10(step0)));
  const norm=step0/mag, step=(norm<1.5?1:norm<3?2:norm<7?5:10)*mag;
  const t=[]; for(let v=Math.ceil(lo/step)*step; v<=hi+1e-12; v+=step) t.push(v);
  return t;
}
function setupCanvas(parent,h){
  const c=document.createElement('canvas'); parent.appendChild(c);
  const tip=document.createElement('div'); tip.className='tip'; parent.appendChild(tip);
  const resize=()=>{const w=parent.clientWidth, dpr=window.devicePixelRatio||1;
    c.width=w*dpr; c.height=h*dpr; c.style.height=h+'px';
    c.getContext('2d').setTransform(dpr,0,0,dpr,0,0);};
  resize(); window.addEventListener('resize',()=>{resize(); if(c._draw) c._draw();});
  return {c,tip,ctx:c.getContext('2d'),h};
}

class LineChart{
  /* series: [{name,dates,values,color,width,fill,dash}] */
  constructor(el,series,opts={}){
    this.el=document.getElementById(el); this.s=series; this.o=opts;
    const {c,tip,ctx,h}=setupCanvas(this.el,opts.height||300);
    this.c=c; this.tip=tip; this.ctx=ctx; this.h=h;
    this.s.forEach(sr=>{sr.t=sr.dates.map(ts); sr.on=true;});
    this.log=false; this.zoom=null;
    this.pad={l:56,r:14,t:10,b:22};
    c._draw=()=>this.draw();
    this.bindMouse(); this.buildLegend(); this.draw();
  }
  domain(){
    let lo=Infinity,hi=-Infinity,vlo=Infinity,vhi=-Infinity;
    for(const sr of this.s){ if(!sr.on) continue;
      for(let i=0;i<sr.t.length;i++){
        const t=sr.t[i],v=sr.values[i];
        if(this.zoom&&(t<this.zoom[0]||t>this.zoom[1])) continue;
        if(v==null) continue;
        if(t<lo)lo=t; if(t>hi)hi=t;
        if(v<vlo)vlo=v; if(v>vhi)vhi=v;
      }}
    if(!isFinite(lo)){lo=0;hi=1;vlo=0;vhi=1;}
    if(this.o.y0!==undefined) vlo=Math.min(vlo,this.o.y0);
    if(this.o.yMax!==undefined) vhi=Math.max(vhi,this.o.yMax);
    if(vhi-vlo<1e-12) vhi=vlo+1;
    const padv=(vhi-vlo)*0.06; return [lo,hi,vlo-padv,vhi+padv];
  }
  sx(t){const[lo,hi]=this.dom; const W=this.c.clientWidth-this.pad.l-this.pad.r;
    return this.pad.l+(t-lo)/(hi-lo)*W;}
  sy(v){const[, ,vlo,vhi]=this.dom; const H=this.h-this.pad.t-this.pad.b;
    if(this.log){const a=Math.log(Math.max(vlo,1e-9)),b=Math.log(vhi);
      return this.pad.t+H-(Math.log(Math.max(v,1e-9))-a)/(b-a)*H;}
    return this.pad.t+H-(v-vlo)/(vhi-vlo)*H;}
  draw(){
    const ctx=this.ctx,W=this.c.clientWidth,H=this.h;
    ctx.clearRect(0,0,W,H); this.dom=this.domain();
    const[lo,hi,vlo,vhi]=this.dom;
    // regime bands
    if(this.o.regimeBands){
      const spanDays=(hi-lo)/86400000;
      const minSeg=spanDays/220;  // hide stress slivers thinner than ~1px at this zoom
      for(const sg of DATA.regime.segments){
        if(sg.r===0) continue;  // Bull = clean background; shade stress only
        const a=Math.max(ts(sg.a),lo),b=Math.min(ts(sg.b),hi);
        if(b<=a) continue;
        if((b-a)/86400000 < minSeg) continue;
        ctx.fillStyle=REGCOL[sg.r];
        ctx.fillRect(this.sx(a),this.pad.t,this.sx(b)-this.sx(a),H-this.pad.t-this.pad.b);
      }}
    // gridlines + y ticks
    ctx.font='10.5px ui-monospace,Menlo,monospace'; ctx.fillStyle='#5b6a84';
    const yt=this.log?logTicks(vlo,vhi):niceTicks(vlo,vhi,5);
    ctx.strokeStyle='#16223a'; ctx.lineWidth=1;
    for(const v of yt){const y=this.sy(v); if(y<this.pad.t-1||y>H-this.pad.b+1)continue;
      ctx.beginPath();ctx.moveTo(this.pad.l,y);ctx.lineTo(W-this.pad.r,y);ctx.stroke();
      ctx.fillText((this.o.fmt||fmt.num)(v),6,y+3);}
    // x ticks: year boundaries
    const y0=new Date(lo).getUTCFullYear(),y1=new Date(hi).getUTCFullYear();
    const step=Math.max(1,Math.ceil((y1-y0)/8));
    ctx.textAlign='center';
    for(let y=y0;y<=y1;y+=step){const t=Date.UTC(y,0,1); if(t<lo||t>hi)continue;
      const x=this.sx(t); ctx.strokeStyle='#141f36'; ctx.beginPath();
      ctx.moveTo(x,this.pad.t);ctx.lineTo(x,H-this.pad.b);ctx.stroke();
      ctx.fillText(y,x,H-7);}
    ctx.textAlign='left';
    // hline at y=hline
    if(this.o.hline!==undefined&&this.o.hline>=vlo&&this.o.hline<=vhi){
      ctx.strokeStyle='#3d4d68'; ctx.setLineDash([5,4]); ctx.beginPath();
      const y=this.sy(this.o.hline);
      ctx.moveTo(this.pad.l,y);ctx.lineTo(W-this.pad.r,y);ctx.stroke();ctx.setLineDash([]);}
    if(this.o.hlines) for(const hl of this.o.hlines){
      if(hl.v<vlo||hl.v>vhi) continue;
      ctx.strokeStyle=hl.color||'#3d4d68'; ctx.setLineDash([5,4]); ctx.beginPath();
      const y=this.sy(hl.v); ctx.moveTo(this.pad.l,y);ctx.lineTo(W-this.pad.r,y);
      ctx.stroke();ctx.setLineDash([]);}
    // band fills (pairs of series indices) drawn beneath the lines
    if(this.o.bands){
      for(const bd of this.o.bands){
        const su=this.s[bd.u], sl=this.s[bd.l];
        ctx.beginPath(); let st=false;
        for(let i=0;i<su.t.length;i++){const v=su.values[i];
          if(v==null) continue; const t=su.t[i]; if(t<lo||t>hi) continue;
          const x=this.sx(t),y=this.sy(v);
          st?ctx.lineTo(x,y):ctx.moveTo(x,y); st=true;}
        for(let i=sl.t.length-1;i>=0;i--){const v=sl.values[i];
          if(v==null) continue; const t=sl.t[i]; if(t<lo||t>hi) continue;
          ctx.lineTo(this.sx(t),this.sy(v));}
        ctx.closePath(); ctx.fillStyle=bd.color; ctx.fill();
      }}
    // series
    for(const sr of this.s){ if(!sr.on) continue;
      ctx.beginPath(); let started=false;
      for(let i=0;i<sr.t.length;i++){const v=sr.values[i];
        if(v==null){started=false;continue;}
        const t=sr.t[i]; if(t<lo||t>hi) continue;
        const x=this.sx(t),y=this.sy(v);
        if(!started){ctx.moveTo(x,y);started=true;} else ctx.lineTo(x,y);}
      ctx.strokeStyle=sr.color; ctx.lineWidth=sr.width||1.7;
      if(sr.dash)ctx.setLineDash(sr.dash);
      ctx.stroke(); ctx.setLineDash([]);
      if(sr.fill){ctx.lineTo(this.sx(hi),this.sy(this.o.fillTo??0));
        ctx.lineTo(this.sx(lo),this.sy(this.o.fillTo??0)); ctx.closePath();
        ctx.fillStyle=sr.color+'26'; ctx.fill();}}
    // zoom selection overlay
    if(this.selA!=null&&this.selB!=null){
      ctx.fillStyle='#27d3ee14';
      ctx.fillRect(Math.min(this.selA,this.selB),this.pad.t,
                   Math.abs(this.selB-this.selA),H-this.pad.t-this.pad.b);}
  }
  bindMouse(){
    const c=this.c;
    c.addEventListener('mousemove',e=>{
      const r=c.getBoundingClientRect(),x=e.clientX-r.left;
      if(this.dragging){this.selB=x;this.draw();return;}
      this.crosshair(x,e.clientY-r.top);});
    c.addEventListener('mouseleave',()=>{this.tip.style.display='none';this.draw();});
    c.addEventListener('mousedown',e=>{const r=c.getBoundingClientRect();
      this.dragging=true;this.selA=e.clientX-r.left;this.selB=null;});
    window.addEventListener('mouseup',()=>{
      if(!this.dragging)return; this.dragging=false;
      if(this.selB!=null&&Math.abs(this.selB-this.selA)>12){
        const[lo,hi]=this.dom,W=c.clientWidth-this.pad.l-this.pad.r;
        const t1=lo+(Math.min(this.selA,this.selB)-this.pad.l)/W*(hi-lo);
        const t2=lo+(Math.max(this.selA,this.selB)-this.pad.l)/W*(hi-lo);
        this.zoom=[t1,t2];}
      this.selA=this.selB=null; this.draw();});
    c.addEventListener('dblclick',()=>{this.zoom=null;this.draw();});
  }
  crosshair(x,y){
    this.draw();
    const ctx=this.ctx,[lo,hi]=this.dom;
    if(x<this.pad.l||x>this.c.clientWidth-this.pad.r){this.tip.style.display='none';return;}
    const W=this.c.clientWidth-this.pad.l-this.pad.r;
    const t=lo+(x-this.pad.l)/W*(hi-lo);
    ctx.strokeStyle='#3a4a66'; ctx.setLineDash([3,3]);
    ctx.beginPath();ctx.moveTo(x,this.pad.t);ctx.lineTo(x,this.h-this.pad.b);ctx.stroke();
    ctx.setLineDash([]);
    let rows='',dstr='';
    for(const sr of this.s){ if(!sr.on) continue;
      let i=bisect(sr.t,t); if(i<0) continue;
      const v=sr.values[i]; if(v==null) continue;
      dstr=sr.dates[i];
      ctx.beginPath();ctx.arc(this.sx(sr.t[i]),this.sy(v),3,0,7);ctx.fillStyle=sr.color;ctx.fill();
      rows+=`<div class="r"><span style="color:${sr.color}">${sr.name}</span><b>${(this.o.fmt||fmt.num)(v)}</b></div>`;}
    if(!rows){this.tip.style.display='none';return;}
    this.tip.innerHTML=`<div class="d">${dstr}</div>`+rows;
    this.tip.style.display='block';
    const tw=this.tip.offsetWidth;
    this.tip.style.left=Math.min(x+14,this.c.clientWidth-tw-6)+'px';
    this.tip.style.top=(this.pad.t+8)+'px';
  }
  buildLegend(){
    if(!this.o.legend) return;
    const el=document.getElementById(this.o.legend); if(!el) return;
    for(const sr of this.s){
      const sp=document.createElement('span');
      sp.innerHTML=`<i style="background:${sr.color}"></i>${sr.name}`;
      sp.onclick=()=>{sr.on=!sr.on;sp.classList.toggle('off');this.draw();};
      el.appendChild(sp);}
  }
}
function bisect(arr,t){
  let lo=0,hi=arr.length-1; if(t<=arr[0])return 0; if(t>=arr[hi])return hi;
  while(hi-lo>1){const m=(lo+hi)>>1; if(arr[m]<t)lo=m; else hi=m;}
  return (t-arr[lo]<arr[hi]-t)?lo:hi;
}
function logTicks(lo,hi){
  const t=[]; let v=Math.pow(10,Math.floor(Math.log10(Math.max(lo,1e-9))));
  while(v<=hi*1.01){ for(const m of [1,2,5]){const x=v*m; if(x>=lo&&x<=hi)t.push(x);} v*=10;}
  return t.length?t:[lo,hi];
}

class StackedArea{
  constructor(el,dates,series,opts={}){
    this.el=document.getElementById(el);
    const {c,tip,ctx,h}=setupCanvas(this.el,opts.height||240);
    this.c=c;this.tip=tip;this.ctx=ctx;this.h=h;this.o=opts;
    this.dates=dates; this.t=dates.map(ts); this.series=series;
    this.pad={l:46,r:12,t:8,b:22};
    c._draw=()=>this.draw();
    c.addEventListener('mousemove',e=>{const r=c.getBoundingClientRect();
      this.hover(e.clientX-r.left);});
    c.addEventListener('mouseleave',()=>{this.tip.style.display='none';this.draw();});
    this.buildLegend(); this.draw();
  }
  sx(i){const W=this.c.clientWidth-this.pad.l-this.pad.r;
    return this.pad.l+(this.t[i]-this.t[0])/(this.t[this.t.length-1]-this.t[0]||1)*W;}
  sy(v){const H=this.h-this.pad.t-this.pad.b;return this.pad.t+H-v*H;}
  draw(){
    const ctx=this.ctx,W=this.c.clientWidth,H=this.h,n=this.t.length;
    ctx.clearRect(0,0,W,H);
    let base=new Array(n).fill(0);
    for(const sr of this.series){
      ctx.beginPath();
      for(let i=0;i<n;i++){const x=this.sx(i),y=this.sy(base[i]+(sr.values[i]||0));
        i?ctx.lineTo(x,y):ctx.moveTo(x,y);}
      for(let i=n-1;i>=0;i--) ctx.lineTo(this.sx(i),this.sy(base[i]));
      ctx.closePath(); ctx.fillStyle=sr.color+'cc'; ctx.fill();
      for(let i=0;i<n;i++) base[i]+=sr.values[i]||0;}
    // x ticks
    ctx.font='10.5px ui-monospace,Menlo,monospace';ctx.fillStyle='#5b6a84';ctx.textAlign='center';
    const y0=new Date(this.t[0]).getUTCFullYear(),y1=new Date(this.t[n-1]).getUTCFullYear();
    const step=Math.max(1,Math.ceil((y1-y0)/8));
    for(let y=y0;y<=y1;y+=step){const tt=Date.UTC(y,0,1);
      if(tt<this.t[0]||tt>this.t[n-1])continue;
      const i=bisect(this.t,tt); ctx.fillText(y,this.sx(i),H-7);}
    ctx.textAlign='left';
    for(const f of [0,0.5,1]){ctx.fillText((f*100).toFixed(0)+'%',8,this.sy(f)+3);}
  }
  hover(x){
    this.draw();
    const n=this.t.length,W=this.c.clientWidth-this.pad.l-this.pad.r;
    const tt=this.t[0]+(x-this.pad.l)/W*(this.t[n-1]-this.t[0]);
    const i=bisect(this.t,tt);
    const ctx=this.ctx; ctx.strokeStyle='#3a4a66';ctx.setLineDash([3,3]);
    ctx.beginPath();ctx.moveTo(this.sx(i),this.pad.t);ctx.lineTo(this.sx(i),this.h-this.pad.b);
    ctx.stroke();ctx.setLineDash([]);
    let rows='';
    for(const sr of this.series)
      rows+=`<div class="r"><span style="color:${sr.color}">${sr.name}</span><b>${((sr.values[i]||0)*100).toFixed(0)}%</b></div>`;
    if(this.o.extra) rows+=this.o.extra(i);
    this.tip.innerHTML=`<div class="d">${this.dates[i]}</div>`+rows;
    this.tip.style.display='block';
    const tw=this.tip.offsetWidth;
    this.tip.style.left=Math.min(x+14,this.c.clientWidth-tw-6)+'px';
    this.tip.style.top=(this.pad.t+6)+'px';
  }
  buildLegend(){
    if(!this.o.legend)return; const el=document.getElementById(this.o.legend); if(!el)return;
    for(const sr of this.series){
      const sp=document.createElement('span');
      sp.innerHTML=`<i style="background:${sr.color}"></i>${sr.name}`;
      el.appendChild(sp);}
  }
}

/* diverging color for heatmaps */
function divColor(v,lim){
  const x=Math.max(-1,Math.min(1,v/lim));
  if(x>=0){const a=Math.round(40+x*160); return `rgba(52,211,153,${0.08+x*0.8})`;}
  return `rgba(251,113,133,${0.08-x*0.8})`;
}

/* ================================ build ui ================================= */
const $=id=>document.getElementById(id);
// set element markup from our own generated payload (numeric research data)
const setHTML=(id,html)=>{const e=$(id);if(e){e.replaceChildren();e.insertAdjacentHTML('afterbegin',html);}};
const meta=DATA.meta, S=DATA.series, ST=DATA.stats;

$('b-src').textContent=meta.source+' DATA';
$('b-src').className='badge '+(meta.source==='YAHOO'?'live':'');
$('b-range').textContent=meta.range[0]+' → '+meta.range[1];
$('b-uni').textContent=meta.n_assets+' ASSETS · '+meta.trading_days+' DAYS';
$('b-regime').textContent='REGIME: '+meta.current_regime.toUpperCase();
$('b-regime').className='badge regime-'+meta.current_regime;
$('f-gen').textContent=meta.generated;

/* hero cards */
const k=ST['KRONOS (net)'];
const cards=[
  {k:'CAGR (net)',v:fmt.pct(k.cagr),cls:k.cagr>=0?'pos':'neg',s:'SPY '+fmt.pct(ST.SPY.cagr),sp:S.nav_net},
  {k:'Sharpe',v:k.sharpe.toFixed(2),cls:'neu',s:'SPY '+ST.SPY.sharpe.toFixed(2),sp:S.roll_sharpe},
  {k:'Sortino',v:k.sortino.toFixed(2),cls:'neu',s:'Calmar '+k.calmar.toFixed(2),sp:S.roll_sharpe},
  {k:'Max Drawdown',v:fmt.pct(k.max_dd),cls:'neg',s:'SPY '+fmt.pct(ST.SPY.max_dd),sp:S.drawdown},
  {k:'CVaR 95 (daily)',v:fmt.pct2(k.cvar95),cls:'neg',s:'VaR '+fmt.pct2(k.var95),sp:S.roll_vol},
  {k:'Volatility',v:fmt.pct(k.vol),cls:'neu',s:'target '+fmt.pct(meta.vol_target),sp:S.roll_vol},
  {k:'Turnover',v:meta.ann_turnover.toFixed(1)+'×/yr',cls:'neu',s:'rebalance '+meta.rebalance_days+'d',sp:S.exposure},
  {k:'Cost Drag',v:fmt.pct2(meta.ann_cost)+'/yr',cls:'neg',s:'commission + spread + impact',sp:S.exposure},
];
for(const cd of cards){
  const d=document.createElement('div');d.className='card';
  d.innerHTML=`<div class="k">${cd.k}</div><div class="v mono ${cd.cls}">${cd.v}</div>
    <div class="s">${cd.s}</div><canvas></canvas>`;
  $('cards').appendChild(d);
  const cv=d.querySelector('canvas');
  const drawSpark=()=>{
    const dpr=window.devicePixelRatio||1,w=cv.clientWidth||150;
    cv.width=w*dpr;cv.height=26*dpr;
    const cx=cv.getContext('2d');cx.setTransform(dpr,0,0,dpr,0,0);
    const vals=cd.sp.values.filter(v=>v!=null);
    const mn=Math.min(...vals),mx=Math.max(...vals);
    cx.beginPath();
    vals.forEach((v,i)=>{const x=i/(vals.length-1)*w,y=24-(v-mn)/(mx-mn||1)*22;
      i?cx.lineTo(x,y):cx.moveTo(x,y);});
    cx.strokeStyle='#27d3ee';cx.lineWidth=1.2;cx.stroke();
  };
  requestAnimationFrame(drawSpark);
  window.addEventListener('resize',drawSpark);
}

/* equity + drawdown */
const eq=new LineChart('ch-eq',[
  {name:'KRONOS net',dates:S.nav_net.dates,values:S.nav_net.values,color:COL.cyan,width:2.2},
  {name:'KRONOS gross',dates:S.nav_gross.dates,values:S.nav_gross.values,color:COL.violet,width:1.2,dash:[4,3]},
  {name:'SPY',dates:S.nav_spy.dates,values:S.nav_spy.values,color:COL.dim,width:1.4},
  {name:'Equal-weight',dates:S.nav_ew.dates,values:S.nav_ew.values,color:COL.orange,width:1.2,dash:[2,3]},
],{height:340,fmt:fmt.nav,regimeBands:true,legend:'lg-eq'});
$('logbtn').onclick=()=>{eq.log=!eq.log;$('logbtn').classList.toggle('on');eq.draw();};
new LineChart('ch-dd',[
  {name:'KRONOS DD',dates:S.drawdown.dates,values:S.drawdown.values,color:COL.rose,width:1.5,fill:true},
  {name:'SPY DD',dates:S.dd_spy.dates,values:S.dd_spy.values,color:COL.dim,width:1,dash:[3,3]},
],{height:120,fmt:fmt.pct,fillTo:0});

/* regime stacked probabilities */
(function(){
  const d=S.prob_bull.dates;
  new StackedArea('ch-rg',d,[
    {name:'Bull',values:S.prob_bull.values,color:COL.green},
    {name:'Volatile',values:S.prob_vol.values,color:COL.amber},
    {name:'Bear',values:S.prob_bear.values,color:COL.rose},
  ],{height:260,legend:'lg-rg'});
})();

/* transition matrix */
(function(){
  const el=$('ch-tm'),A=DATA.regime.transition,N=DATA.regime.names;
  const {c,ctx}=setupCanvas(el,200);
  c._draw=()=>{
    const w=c.clientWidth,cell=Math.min((w-70)/3,42);
    ctx.clearRect(0,0,w,200);
    ctx.font='11px ui-monospace,Menlo,monospace';
    for(let i=0;i<3;i++)for(let j=0;j<3;j++){
      const x=64+j*(cell+5),y=30+i*(cell+5),v=A[i][j];
      ctx.fillStyle=`rgba(39,211,238,${0.06+v*0.85})`;
      ctx.fillRect(x,y,cell,cell);
      ctx.fillStyle=v>0.5?'#06202a':'#9fb4d0';ctx.textAlign='center';
      ctx.fillText((v*100).toFixed(1),x+cell/2,y+cell/2+4);}
    ctx.fillStyle='#7d8ca3';ctx.textAlign='right';
    for(let i=0;i<3;i++)ctx.fillText(N[i],58,30+i*(cell+5)+cell/2+4);
    ctx.textAlign='center';
    for(let j=0;j<3;j++)ctx.fillText(N[j],64+j*(cell+5)+cell/2,20);
  };
  c._draw();
})();

/* per-regime table */
(function(){
  let h='<tr><th>Regime</th><th>Days</th><th>KRONOS ann.</th><th>Sharpe</th><th>SPY ann.</th><th>SPY Sharpe</th></tr>';
  for(const r of DATA.regime.per_regime){
    const col=r.name==='Bull'?COL.green:r.name==='Volatile'?COL.amber:COL.rose;
    h+=`<tr><td style="color:${col}">${r.name}</td><td>${r.days}</td>
      <td>${(r.kronos_ann*100).toFixed(1)}%</td><td>${r.kronos_sharpe.toFixed(2)}</td>
      <td>${(r.spy_ann*100).toFixed(1)}%</td><td>${r.spy_sharpe.toFixed(2)}</td></tr>`;}
  $('tbl-regime').innerHTML=h;
})();

/* sleeves */
(function(){
  const cmap={momentum:COL.blue,mean_reversion:COL.amber,low_vol:COL.green,pairs:COL.violet};
  const series=Object.entries(DATA.sleeves).map(([k,v])=>({
    name:k.replace('_',' '),dates:v.dates,values:v.values,color:cmap[k]||COL.dim,width:1.6}));
  new LineChart('ch-sl',series,{height:280,fmt:fmt.nav,legend:'lg-sl'});
})();

/* strategy weights stacked */
(function(){
  const sw=DATA.strategy_weights;
  new StackedArea('ch-sw',sw.dates,[
    {name:'momentum',values:sw.series.momentum,color:COL.blue},
    {name:'mean reversion',values:sw.series.mean_reversion,color:COL.amber},
    {name:'low vol',values:sw.series.low_vol,color:COL.green},
  ],{height:280,extra:i=>`<div class="r"><span>regime</span><b>${sw.regime[i]}</b></div>`});
})();

/* latest weights bars */
(function(){
  const P=DATA.portfolio,el=$('ch-w');
  $('sub-port').textContent='as of '+meta.range[1]+' · '+P.tickers.length+
    ' positions · max weight cap 12%';
  const h=Math.max(160,P.tickers.length*21+30);
  const {c,ctx,tip}=setupCanvas(el,h);
  c._draw=()=>{
    const w=c.clientWidth; ctx.clearRect(0,0,w,h);
    const mx=Math.max(...P.weights),bw=w-130;
    ctx.font='11.5px ui-monospace,Menlo,monospace';
    P.tickers.forEach((tk,i)=>{
      const y=12+i*21,wd=P.weights[i]/mx*bw;
      const g=ctx.createLinearGradient(64,0,64+wd,0);
      g.addColorStop(0,'#1797ad');g.addColorStop(1,'#27d3ee');
      ctx.fillStyle=g; ctx.beginPath();
      ctx.roundRect(64,y,Math.max(wd,2),13,3); ctx.fill();
      ctx.fillStyle='#9fb4d0';ctx.textAlign='right';ctx.fillText(tk,58,y+10);
      ctx.textAlign='left';ctx.fillText((P.weights[i]*100).toFixed(1)+'%',70+wd,y+10);});
  };
  c._draw();
})();

/* weight history heatmap */
(function(){
  const H=DATA.portfolio.heat,el=$('ch-wh');
  const rows=H.tickers.length,hh=Math.max(180,rows*16+40);
  const {c,ctx,tip}=setupCanvas(el,hh);
  const draw=()=>{
    const w=c.clientWidth;ctx.clearRect(0,0,w,hh);
    const x0=56,cw=(w-x0-8)/H.dates.length,ch=16;
    ctx.font='10px ui-monospace,Menlo,monospace';
    H.tickers.forEach((tk,i)=>{
      ctx.fillStyle='#7d8ca3';ctx.textAlign='right';ctx.fillText(tk,x0-5,14+i*ch+11);
      H.values[i].forEach((v,j)=>{
        ctx.fillStyle=`rgba(39,211,238,${Math.min(1,v*9)})`;
        ctx.fillRect(x0+j*cw,14+i*ch,Math.ceil(cw),ch-2);});});
    ctx.textAlign='center';ctx.fillStyle='#5b6a84';
    const stepj=Math.ceil(H.dates.length/8);
    for(let j=0;j<H.dates.length;j+=stepj)
      ctx.fillText(H.dates[j].slice(0,4),x0+j*cw+cw/2,hh-8);
  };
  c._draw=draw; draw();
  c.addEventListener('mousemove',e=>{
    const r=c.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
    const x0=56,cw=(c.clientWidth-x0-8)/H.dates.length;
    const j=Math.floor((x-x0)/cw),i=Math.floor((y-14)/16);
    if(i<0||i>=H.tickers.length||j<0||j>=H.dates.length){tip.style.display='none';return;}
    tip.innerHTML=`<div class="d">${H.dates[j]}</div><div class="r"><span>${H.tickers[i]}</span><b>${(H.values[i][j]*100).toFixed(1)}%</b></div>`;
    tip.style.display='block';
    tip.style.left=Math.min(x+12,c.clientWidth-130)+'px';tip.style.top=(y+10)+'px';});
  c.addEventListener('mouseleave',()=>tip.style.display='none');
})();

/* risk engine */
new LineChart('ch-rk',[
  {name:'exposure',dates:S.exposure.dates,values:S.exposure.values,color:COL.cyan,width:2,fill:true},
  {name:'vol throttle',dates:S.m_vol.dates,values:S.m_vol.values,color:COL.blue,width:1,dash:[3,3]},
  {name:'CVaR throttle',dates:S.m_cvar.dates,values:S.m_cvar.values,color:COL.amber,width:1,dash:[3,3]},
  {name:'DD throttle',dates:S.m_dd.dates,values:S.m_dd.values,color:COL.rose,width:1,dash:[3,3]},
],{height:230,fmt:fmt.pct,legend:'lg-rk',y0:0,yMax:1.05,fillTo:0,regimeBands:true});

new LineChart('ch-vol',[
  {name:'realized vol (63d)',dates:S.roll_vol.dates,values:S.roll_vol.values,color:COL.cyan,width:1.8,fill:true},
],{height:190,fmt:fmt.pct,hline:DATA.risk.vol_target,y0:0,fillTo:0});

/* histogram */
(function(){
  const el=$('ch-hist'),R=DATA.risk;
  const {c,ctx,tip}=setupCanvas(el,190);
  c._draw=()=>{
    const w=c.clientWidth,h=190,p={l:10,r:10,t:8,b:20};
    ctx.clearRect(0,0,w,h);
    const n=R.hist_counts.length,mx=Math.max(...R.hist_counts);
    const e0=R.hist_edges[0],e1=R.hist_edges[n];
    const X=v=>p.l+(v-e0)/(e1-e0)*(w-p.l-p.r);
    for(let i=0;i<n;i++){
      const x=X(R.hist_edges[i]),x2=X(R.hist_edges[i+1]);
      const bh=R.hist_counts[i]/mx*(h-p.t-p.b);
      const mid=(R.hist_edges[i]+R.hist_edges[i+1])/2;
      ctx.fillStyle=mid<-R.var95?'#fb7185bb':mid<0?'#fb718555':'#34d39966';
      ctx.fillRect(x,h-p.b-bh,Math.max(x2-x-1,1),bh);}
    let li=0;
    for(const[v,lb,col] of [[-R.var95,'VaR95',COL.amber],[-R.cvar95,'CVaR95',COL.rose]]){
      ctx.strokeStyle=col;ctx.setLineDash([4,3]);ctx.beginPath();
      ctx.moveTo(X(v),p.t);ctx.lineTo(X(v),h-p.b);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle=col;ctx.font='10px ui-monospace,Menlo,monospace';
      ctx.textAlign='right';ctx.fillText(lb,X(v)-3,p.t+10+li*12);li++;}
    ctx.fillStyle='#5b6a84';ctx.textAlign='center';
    for(const v of [-0.02,-0.01,0,0.01,0.02]){
      if(v<e0||v>e1)continue;ctx.fillText((v*100).toFixed(0)+'%',X(v),h-6);}
  };
  c._draw();
})();

/* greeks */
(function(){
  const G=DATA.greeks;
  const items=[
    {k:'Delta (β to SPY)',v:G.delta.toFixed(2),s:'market sensitivity'},
    {k:'Gamma',v:G.gamma.toFixed(2),s:'convexity to market moves'},
    {k:'Vega',v:(G.vega*100).toFixed(2)+'bp',s:'per vol-point change'},
    {k:'Theta',v:(G.theta*1e4).toFixed(2)+'bp/d',s:'expected cost decay'},
  ];
  for(const it of items){
    const d=document.createElement('div');d.className='greek';
    d.innerHTML=`<div class="k">${it.k}</div><div class="g mono neu">${it.v}</div><div class="s">${it.s}</div>`;
    $('greeks').appendChild(d);}
})();
new LineChart('ch-beta',[
  {name:'60d beta',dates:S.roll_beta.dates,values:S.roll_beta.values,color:COL.violet,width:1.8},
],{height:170,fmt:fmt.num,hline:0,regimeBands:true});

/* pairs */
(function(){
  const P=DATA.pairs;
  const tr=(P.total_return*100).toFixed(1);
  $('sub-pairs').textContent=P.n_trades+' trade events · annual re-selection · '+
    `entry |z|>${P.entry} · exit |z|<${P.exit} · stop |z|>${P.stop} · `+
    `sleeve total ${tr>=0?'+':''}${tr}% · spread: `+P.z_example.pair;
  if(P.z_example.dates.length)
    new LineChart('ch-z',[
      {name:'z '+P.z_example.pair,dates:P.z_example.dates,values:P.z_example.z,color:COL.cyan,width:1.4},
    ],{height:200,fmt:fmt.z,hlines:[
      {v:P.entry,color:'#fbbf2477'},{v:-P.entry,color:'#fbbf2477'},
      {v:P.exit,color:'#34d39955'},{v:-P.exit,color:'#34d39955'},
      {v:P.stop,color:'#fb718577'},{v:-P.stop,color:'#fb718577'}]});
  let h='<tr><th>Pair</th><th>Pos</th><th>β (Kalman)</th><th>Status</th></tr>';
  for(const r of P.table){
    h+=`<tr><td>${r.y} / ${r.x}</td>
      <td>${r.pos>0?'<span class="pos">long</span>':r.pos<0?'<span class="neg">short</span>':'flat'}</td>
      <td class="mono">${r.beta.toFixed(2)}</td>
      <td>${r.dead?'<span class="neg">stopped</span>':'<span class="pos">live</span>'}</td></tr>`;}
  $('tbl-pairs').innerHTML=h;
})();

/* ===================== generic numeric-x chart (research) ================== */
function XYChart(el,series,opts={}){
  const parent=document.getElementById(el);
  const {c,ctx}=setupCanvas(parent,opts.height||230);
  const draw=()=>{
    const W=c.clientWidth,H=opts.height||230,p={l:52,r:12,t:10,b:26};
    ctx.clearRect(0,0,W,H);
    let xlo=Infinity,xhi=-Infinity,ylo=Infinity,yhi=-Infinity;
    for(const sr of series){
      for(let i=0;i<sr.x.length;i++){
        if(sr.x[i]<xlo)xlo=sr.x[i]; if(sr.x[i]>xhi)xhi=sr.x[i];
        if(sr.y[i]<ylo)ylo=sr.y[i]; if(sr.y[i]>yhi)yhi=sr.y[i];}}
    if(opts.y0!==undefined) ylo=Math.min(ylo,opts.y0);
    if(xhi-xlo<1e-12)xhi=xlo+1; if(yhi-ylo<1e-12)yhi=ylo+1;
    const padY=(yhi-ylo)*0.08; ylo-=padY; yhi+=padY;
    const X=v=>p.l+(v-xlo)/(xhi-xlo)*(W-p.l-p.r);
    const Y=v=>p.t+(H-p.t-p.b)*(1-(v-ylo)/(yhi-ylo));
    ctx.font='10.5px ui-monospace,Menlo,monospace';
    ctx.strokeStyle='#16223a';ctx.fillStyle='#5b6a84';
    for(const v of niceTicks(ylo,yhi,5)){
      if(v<ylo||v>yhi)continue;
      ctx.beginPath();ctx.moveTo(p.l,Y(v));ctx.lineTo(W-p.r,Y(v));ctx.stroke();
      ctx.fillText((opts.yfmt||(x=>x.toFixed(2)))(v),4,Y(v)+3);}
    ctx.textAlign='center';
    for(const v of niceTicks(xlo,xhi,7)){
      if(v<xlo||v>xhi)continue;
      ctx.fillText((opts.xfmt||(x=>x.toFixed(1)))(v),X(v),H-8);}
    ctx.textAlign='left';
    if(opts.xlabel){ctx.fillStyle='#46546b';ctx.textAlign='center';
      ctx.fillText(opts.xlabel,(p.l+W-p.r)/2,H-0.5);ctx.textAlign='left';}
    for(const sr of series){
      if(sr.bars){ // histogram-style bars
        const bw=sr.binw!==undefined?X(xlo+sr.binw)-X(xlo):4;
        ctx.fillStyle=sr.color;
        for(let i=0;i<sr.x.length;i++)
          ctx.fillRect(X(sr.x[i])-bw/2,Y(sr.y[i]),Math.max(bw-1,1),Y(ylo+padY)-Y(sr.y[i]));
        continue;}
      ctx.beginPath();
      for(let i=0;i<sr.x.length;i++){const x=X(sr.x[i]),y=Y(sr.y[i]);
        i?ctx.lineTo(x,y):ctx.moveTo(x,y);}
      ctx.strokeStyle=sr.color;ctx.lineWidth=sr.width||1.7;
      if(sr.dash)ctx.setLineDash(sr.dash);
      ctx.stroke();ctx.setLineDash([]);
      if(sr.points){ctx.fillStyle=sr.color;
        for(let i=0;i<sr.x.length;i++){
          ctx.beginPath();ctx.arc(X(sr.x[i]),Y(sr.y[i]),3,0,7);ctx.fill();}}}
    // inline legend
    let lx=p.l+10;
    for(const sr of series){ if(!sr.name) continue;
      ctx.fillStyle=sr.color;ctx.fillRect(lx,p.t+2,12,3);
      ctx.fillStyle='#9fb4d0';ctx.fillText(sr.name,lx+16,p.t+7);
      lx+=16+ctx.measureText(sr.name).width+18;}
  };
  c._draw=draw; draw();
}

/* ============================= research tab ================================ */
if(DATA.research){
  $('tabbar').style.display='flex';
  let researchBuilt=false;
  document.querySelectorAll('.tab').forEach(tb=>{
    tb.onclick=()=>{
      document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));
      tb.classList.add('on');
      const which=tb.dataset.tab;
      $('tab-overview').style.display=which==='overview'?'':'none';
      $('tab-research').style.display=which==='research'?'':'none';
      if(which==='research'&&!researchBuilt){researchBuilt=true;buildResearch();}
    };
  });
  // deep-link: ?tab=research or #research opens the research tab on load
  const wantTab=(new URLSearchParams(location.search).get('tab'))||location.hash.replace('#','');
  if(wantTab==='research'){const t=document.querySelector('.tab[data-tab="research"]');if(t)t.click();}
}

function buildResearch(){
  const R=DATA.research;
  const pct=v=>(v*100).toFixed(1)+'%';

  /* ---- verdict cards ---- */
  const horse=R.horserace, vol=R.vollab, rough=R.rough, rmt=R.rmt,
        cvar=R.cvar, ens=R.ensemble, forz=R.forensics, syn=R.synthesis,
        sa=R.statarb;
  const qs=[
    {q:'Q1 — More than 3 regimes?', v:'MIXED', cls:'verdict-mixed',
     d:`HMM predictive log-score keeps rising to K=5 (${horse.ksweep.HMM["5"].toFixed(3)}) but SJM peaks at K=3 — extra HMM states model fat tails, not new economic regimes.`},
    {q:'Q2 — Do explicit durations beat the HMM?', v:'NO', cls:'verdict-no',
     d:`DurHMM ties plain HMM out of sample (${horse.models["DurHMM-3x3"].logscore_oos.toFixed(4)} vs ${horse.models["HMM-3"].logscore_oos.toFixed(4)} nats/day). Honest negative — the test had power on synthetic semi-Markov worlds.`},
    {q:'Q3a — Beat EWMA vol forecasts?', v:'YES — HAR-RV', cls:'verdict-yes',
     d:`QLIKE ${vol.qlike.har.toFixed(3)} vs ${vol.qlike.ewma.toFixed(3)}, Diebold-Mariano ${vol.dm.har_vs_ewma.stat.toFixed(1)} (p<0.001). GARCH ties HAR.`},
    {q:'Q3b — Is volatility rough?', v:'YES — H ≈ '+rough.daily.H.toFixed(2), cls:'verdict-yes',
     d:`SPY Garman-Klass log-vol scales with H=${rough.daily.H.toFixed(3)}, CI [${rough.daily.ci.ci_lo.toFixed(2)}, ${rough.daily.ci.ci_hi.toFixed(2)}] — replicates Gatheral et al.'s H≈0.1 on our own 16 years.`},
    {q:'Q4 — Does adaptive blending beat regime gates?', v:'NO — ALL TIE', cls:'verdict-mixed',
     d:`Every method lands at Sharpe ≈ ${ens.methods.regime_gates.sharpe.toFixed(2)}. The sleeves are too correlated through the shared HRP backbone for blend weights to matter — the backbone does the work.`},
    {q:'Q5a — RMT denoising beats Ledoit-Wolf?', v:'NO', cls:'verdict-no',
     d:`Min-var realized vol: LW ${pct(rmt.methods.lw.realized_vol)} vs RMT ${pct(rmt.methods.rmt.realized_vol)}. With N=48, T=252 the noise is mild; RMT's bulk-flattening is built for far wider universes.`},
    {q:'Q5b — Min-CVaR LP beats HRP?', v:'MARGINALLY', cls:'verdict-mixed',
     d:`Delivers what it optimizes: realized CVaR ${pct(cvar.cvar_ewma.cvar95)} vs HRP ${pct(cvar.hrp.cvar95)}, Sharpe ${cvar.cvar_ewma.sharpe.toFixed(2)} vs ${cvar.hrp.sharpe.toFixed(2)}.`},
    {q:'Q6 — Is the strategy statistically real?', v:'RETURNS YES, SELECTION NO', cls:'verdict-mixed',
     d:`Bootstrap Sharpe CI [${forz.bootstrap.ci_lo.toFixed(2)}, ${forz.bootstrap.ci_hi.toFixed(2)}] excludes zero — but DSR ${forz.dsr.dsr.toFixed(2)} after ${forz.n_trials} trials: the edge over sibling configurations is not certifiable. PBO ${forz.pbo.pbo.toFixed(2)}.`},
    {q:'Stat-arb — does it still work?', v:'NO — ALPHA DECAYED', cls:'verdict-no',
     d:`Eigenportfolio stat-arb: ${(sa.full.ann_ret*100).toFixed(1)}%/yr (SR ${sa.full.sharpe.toFixed(2)}). The gate proves the machinery extracts planted OU at Sharpe 2.4 — the edge is gone from the market, replicating the documented post-2008 decay.`},
  ];
  if(R.tails){
    const fw=R.tails.mc.fat_world, gw=R.tails.mc.gaussian_world;
    qs.push({q:'X² — Do Gaussian HMMs hallucinate regimes from fat tails?',
      v:'YES', cls:'verdict-yes',
      d:`Monte Carlo (true K=3, t₅ emissions): Gaussian selection overfits K>3 in ${(fw.frac_overfit.gauss*100).toFixed(0)}% of seeds vs ${(fw.frac_overfit.t*100).toFixed(0)}% for the t-HMM (base rate ${(gw.frac_overfit.gauss*100).toFixed(0)}% on Gaussian worlds). Real data: see the K-curves and MCS below.`});
  }
  if(R.rfsv){
    const rf=R.rfsv;
    qs.push({q:'X² — Does roughness forecast?', v:'COMPETITIVE, NOT CHAMPION', cls:'verdict-mixed',
      d:`RFSV (kernel H=${rf.kernel.H.toFixed(2)}) crushes EWMA (AG ${rf.ag.rfsv_vs_ewma.stat.toFixed(1)}), ties GARCH, but HAR wins pairwise (AG ${rf.ag.rfsv_vs_har.stat.toFixed(1)}, p=${rf.ag.rfsv_vs_har.p.toFixed(3)}). RFSV survives the model confidence set; EWMA does not.`});
  }
  if(R.laws){
    const L=R.laws;
    qs.push({q:'LAWS L1 — One clock for all assets?', v:'SURVIVED', cls:'verdict-yes',
      d:`Standardizing by realized vol: median kurtosis 12.6 → ${L.l1.median_kurt_z.toFixed(2)}, fitted ν 3.3 → ${L.l1.median_nu_z.toFixed(0)} across 48 assets. Cross-asset KS distance only ${(L.l1.collapse.ratio).toFixed(2)}× the sampling floor — stocks, bonds, gold, credit collapse onto ONE distribution.`});
    qs.push({q:'LAWS P1b — Do hallucinated regimes die with the tails?', v:'YES — LOOP CLOSED', cls:'verdict-yes',
      d:`On deformed returns the Gaussian K-rise(3→5) goes from ${L.l1.k_rise_raw>=0?'+':''}${L.l1.k_rise_raw.toFixed(4)} to ${L.l1.k_rise_z>=0?'+':''}${L.l1.k_rise_z.toFixed(4)} and all t-HMM ν → Gaussian (${L.l1.nus_z_hmm.join(', ')}). The X² mechanism now has its cause: extra states WERE the vol path's tails.`});
    qs.push({q:'LAWS L2 — Parameter-free kurtosis law?', v:'KILLED (informatively)', cls:'verdict-no',
      d:`Persistent-SV predicts only part of kurtosis: log-corr ${L.l2.log_corr.toFixed(2)}, median excess +${L.l2.median_excess.toFixed(1)}. Most unconditional kurtosis is day-specific (jumps/gaps), not slow SV — yet GK deformation still kills it (L1), because the daily range SEES the jumps.`});
    qs.push({q:'LAWS L3 — Universal multifractality?', v:'SURVIVED (caveat)', cls:'verdict-mixed',
      d:`Intermittency λ² median ${L.l3.median.toFixed(3)}, IQR [${L.l3.iqr[0].toFixed(3)}, ${L.l3.iqr[1].toFixed(3)}] — tightly clustered across all assets (rel spread ${L.l3.rel_spread.toFixed(2)} < 0.5 pre-registered bar). Caveat: fat tails can inflate apparent λ²; needs the deformed-series control before strong claims.`});
  }
  if(R.clock){
    const C=R.clock, vs=C.versions;
    qs.push({q:'CLOCK — Is systemic tail risk just correlated clocks?', v:'YES, BUT THE CLOCKS CRASH TOGETHER', cls:'verdict-mixed',
      d:`Raw: ${(vs.raw.all.q50.frac_above95*100).toFixed(0)}% of pairs exceed the Gaussian null. Given the realized clocks (same-day deformation): ${(vs.same_day.all.q50.frac_above95*100).toFixed(0)}% — the copula is ~Gaussian. But relative to YESTERDAY's clocks (lagged): ${(vs.lagged.all.q50.frac_above95*100).toFixed(0)}% remain — joint crashes are unpredictable common volatility surges, not contagion in the residuals.`});
    qs.push({q:'CLOCK C1 — Was the universal multifractality real?', v:'NO — IT WAS THE CLOCK', cls:'verdict-no',
      d:`λ² goes ${C.c1.lambda2_raw_median.toFixed(3)} → ${C.c1.lambda2_z_median.toFixed(3)} after deformation. All measured intermittency lives in the daily vol path; deformed returns are monofractal. L3's "universality" = the clock's universality.`});
  }
  if(R.surge){
    const S=R.surge;
    qs.push({q:'SURGE S1 — Does the clock have a clock?', v:'YES — BUT THE LAW DOES NOT RECURSE', cls:'verdict-mixed',
      d:`Clock innovations cluster (AC₁|u| = ${S.s1.median_ac1.toFixed(2)}) and are fat (kurt ${S.s1.median_kurt_u.toFixed(1)}) — but meta-deformation does NOT gaussianize them (kurt ${S.s1.median_kurt_z2.toFixed(1)} after). Returns are conditionally Gaussian given vol; vol is NOT conditionally Gaussian given vol-of-vol. The cascade terminates: vol has irreducible jumps.`});
    qs.push({q:'SURGE S2 — The arrow of time (Zumbach)', v:'FAINT IN DAILY BARS', cls:'verdict-mixed',
      d:`Median Z ${S.s2.median_z >= 0 ? '+' : ''}${S.s2.median_z.toFixed(2)}, only ${(S.s2.frac_significant_pos*100).toFixed(0)}% of assets significant (the gate proves the estimator has power on strong asymmetry). The leverage class structure IS clear: SPY L(1-10) ${S.s2.lev10.SPY.toFixed(3)}, GLD ${S.s2.lev10.GLD >= 0 ? '+' : ''}${S.s2.lev10.GLD.toFixed(3)}, TLT +${S.s2.lev10.TLT.toFixed(3)} — equities leverage, safe havens inverse.`});
    qs.push({q:'SURGE S3 — Is surge risk forecastable in intensity?', v:'SUGGESTIVE, NOT SIGNIFICANT', cls:'verdict-mixed',
      d:`Joint-tail days are ${S.s3.lift.toFixed(1)}× more frequent after high meta-clock terciles (${(S.s3.freq_t1*100).toFixed(1)}% → ${(S.s3.freq_t3*100).toFixed(1)}%), but the block-bootstrap CI [${S.s3.ci_lo.toFixed(2)}, ${S.s3.ci_hi.toFixed(2)}] narrowly includes 1. The pre-registered audit fails to overturn CLOCK — by a whisker. Reported as is.`});
  }
  if(R.bits){
    const B=R.bits;
    qs.push({q:'BITS — How much does the market leak?', v:'~0.001 BITS DIRECTION, ~0.4 BITS MAGNITUDE', cls:'verdict-yes',
      d:`The daily sign channel is closed: ${B.direction["1"].bits_net.toFixed(4)} bits/day (not significant; ${B.direction_cross.n_sig}/${B.direction_cross.n_assets} assets pass). The magnitude channel leaks ${B.magnitude.spy_bits.toFixed(2)} bits/day — ~${Math.round(B.magnitude.spy_bits/Math.max(B.direction["1"].bits_net,0.001))}× more. The market tells you how big tomorrow will be, never which way. Direction-only Sharpe ceiling: ${B.ceilings.direction_sr.toFixed(2)} — below buy-and-hold beta.`});
  }
  if(R.trade){
    const T=R.trade, m=T.metrics, fc=m["KRONOS-TRADE (forecast-vol)"], sp=m["SPY (buy & hold)"];
    qs.push({q:'TRADE — Can the research be traded?', v:'YES — RISK-ADJUSTED, NOT A CAGR BET', cls:'verdict-yes',
      d:`The deployable system: Sharpe ${fc.sharpe.toFixed(2)} vs SPY ${sp.sharpe.toFixed(2)} at ${(fc.max_dd*100).toFixed(0)}% max drawdown vs SPY's ${(sp.max_dd*100).toFixed(0)}% — half the pain for comparable risk-adjusted return. Forecast-vol targeting beat the realized-vol control (Sharpe ${T.ab.forecast_sharpe.toFixed(2)} vs ${T.ab.realized_sharpe.toFixed(2)}), confirming the magnitude channel is the edge. It does NOT beat SPY on CAGR (${(fc.cagr*100).toFixed(0)}% vs ${(sp.cagr*100).toFixed(0)}%) — and says so, because the research forbids that claim.`});
  }
  if(R.constants){
    const K=R.constants, Q=K.quantities;
    const nConst=Object.values(Q).filter(r=>r.class==='CONSTANT').length;
    qs.push({q:'CONSTANTS — Do market laws drift (Adaptive Markets)?', v:'MECHANISM IS CONSTANT; ONLY CRISIS-INTENSITY VARIES', cls:'verdict-yes',
      d:`${nConst}/7 laws are statistical constants — the leverage effect, the self-excitation ratio (n=0.65 every era), the one-clock collapse. What varies (roughness, clock commonality, fat tails) is REGIME-driven, peaking in crises (2020), NOT a secular trend — clock commonality even fell afterward, refuting the ETF-ization hypothesis. The only secular drift is crisis-era kurtosis. Markets are stable-with-crisis-regimes, not adaptively evolving.`});
  }
  if(R.reflex){
    const X=R.reflex;
    qs.push({q:'REFLEX — How endogenous is the market?', v:"NEAR-CRITICAL IS A CLUSTERING ILLUSION", cls:'verdict-yes',
      d:`Raw extreme-return branching ratio n=${X.median_n_raw.toFixed(2)} [${X.ci_raw[0].toFixed(2)},${X.ci_raw[1].toFixed(2)}] — near-critical, replicating Filimonov-Sornette. But after deforming out the volatility clock it collapses to n=${X.median_n_def.toFixed(2)} [${X.ci_def[0].toFixed(2)},${X.ci_def[1].toFixed(2)}] — ${(X.clustering_share*100).toFixed(0)}% of apparent endogeneity is clustering. The deformed value sits AT a no-self-excitation null (${X.sv_null_n_def.toFixed(2)}): genuine day-scale jump-cascade reflexivity is statistically absent, did not rise post-2018 (${X.trend.pre.n_def.toFixed(2)}→${X.trend.post.n_def.toFixed(2)}), and is no higher for systemic than idiosyncratic events.`});
  }
  if(R.critical){
    const C=R.critical;
    qs.push({q:'CRITICAL — Are crashes critical transitions or shocks?', v:'SHOCK-DOMINATED, VESTIGIAL TIPPING SIGNATURE', cls:'verdict-mixed',
      d:`After killing the volatility confound, critical-slowing-down indicators add NO robust crash prediction: median incremental AUC ${C.median_gain>=0?'+':''}${C.median_gain.toFixed(4)}, ${(C.frac_pos*100).toFixed(0)}% of 48 assets positive (sign-test p=${C.sign_test_p.toFixed(2)}). The pre-crash φ rises only +${C.precursor.real.phi.toFixed(2)} std — ~8× weaker than a genuine fold bifurcation (+${C.precursor.fold.phi.toFixed(2)} std). The method has power: it convicts a synthetic fold (incremental AUC +${C.gate.fold_gain.toFixed(2)}) and exonerates a synthetic shock (+${C.gate.shock_gain.toFixed(2)}). Crashes are mostly shocks.`});
  }
  if(R.decathlon){
    const D=R.decathlon;
    qs.push({q:'DECATHLON — What is the minimal market?', v:'WILDNESS IS BOUGHT; MEMORY & INFORMATION ARE NOT', cls:'verdict-mixed',
      d:`Vol-targeting reflexivity alone buys the one-sided facts — fat tails, leverage, clock jumps, crash asymmetry (FV: ${D.configs.FV.score}/10); market makers restore efficiency without destroying them (FCVM: ${D.configs.FCVM.score}/10). But NO flow configuration buys long memory, the arrow-in-coupling, or information-free signs — and timescale heterogeneity fails in both implementations (D4 refuted). The missing five events all point at one absent mechanism: anticipatory pricing.`});
  }
  if(R.arrow){
    const A=R.arrow;
    qs.push({q:"ARROW — Where does time's arrow live?", v:'IN THE CLOCK COUPLING — DEFORMATION KILLS IT', cls:'verdict-yes',
      d:`Entropy production (calibrated to closed-form truth, gate X18): raw returns are irreversible for ${A.summary.returns.n_sig}/48 assets (SPY net ${A.spy.returns.net.toFixed(3)} bits), the vol clock for ${A.summary.clock.n_sig}/48 — but DEFORMED returns show ${A.summary.deformed.n_sig}/48 (≈ false-positive rate, median 0.000). The arrow lives in the return↔clock coupling, not the innovations. The general result SURGE's Zumbach statistic was too weak to see.`});
  }
  for(const x of qs){
    const d=document.createElement('div');d.className='qcard';
    d.innerHTML=`<div class="qq">${x.q}</div><div class="qa ${x.cls}">${x.v}</div><div class="qd">${x.d}</div>`;
    $('qcards').appendChild(d);}

  /* ---- horse race table ---- */
  let h='<tr><th>Model</th><th>OOS log-score</th><th>switches/yr</th><th>median dwell</th><th>Sharpe (eval)</th></tr>';
  for(const [m,rec] of Object.entries(horse.models)){
    const win=m===horse.decision.winner;
    h+=`<tr><td${win?' style="color:var(--cyan)"':''}>${m}${win?' ★':''}</td>
      <td>${rec.logscore_oos.toFixed(4)}</td><td>${rec.switches_per_year.toFixed(1)}</td>
      <td>${rec.median_dwell.toFixed(0)}d</td><td>${rec.econ_sharpe_eval.toFixed(2)}</td></tr>`;}
  $('tbl-race').innerHTML=h;

  XYChart('ch-ksweep',[
    {name:'HMM',x:[2,3,4,5],y:[2,3,4,5].map(k=>horse.ksweep.HMM[k]),color:COL.cyan,points:true},
    {name:'SJM',x:[2,3,4,5],y:[2,3,4,5].map(k=>horse.ksweep.SJM[k]),color:COL.amber,points:true},
  ],{height:200,xfmt:v=>'K='+v.toFixed(0),yfmt:v=>v.toFixed(3)});

  let hl='<tr><th>Episode</th>'+Object.keys(horse.models).map(m=>`<th>${m}</th>`).join('')+'</tr>';
  for(const ep of Object.keys(horse.models["HMM-3"].latency)){
    hl+=`<tr><td>${ep}</td>`+Object.values(horse.models).map(r=>
      `<td>${r.latency[ep]}</td>`).join('')+'</tr>';}
  $('tbl-latency').innerHTML=hl;

  /* ---- vol lab ---- */
  $('sub-vollab').textContent=`${vol.n_oos_days} OOS days, QLIKE loss vs GK realized variance; winner: ${vol.winner.toUpperCase()}`;
  let hv='<tr><th>Forecaster</th><th>QLIKE</th><th>DM vs EWMA</th><th>p</th></tr>';
  for(const m of ['ewma','har','garch']){
    const dm=m==='ewma'?null:vol.dm[`${m}_vs_ewma`];
    hv+=`<tr><td${m===vol.winner?' style="color:var(--cyan)"':''}>${m.toUpperCase()}${m===vol.winner?' ★':''}</td>
      <td>${vol.qlike[m].toFixed(4)}</td>
      <td>${dm?dm.stat.toFixed(2):'—'}</td><td>${dm?dm.p.toExponential(1):'—'}</td></tr>`;}
  $('tbl-vollab').innerHTML=hv;
  new LineChart('ch-volfc',[
    {name:'realized (GK)',dates:vol.series.dates,values:vol.series.rv_ann,color:COL.dim,width:1},
    {name:'HAR',dates:vol.series.dates,values:vol.series.har,color:COL.cyan,width:1.4},
    {name:'EWMA',dates:vol.series.dates,values:vol.series.ewma,color:COL.rose,width:1,dash:[3,3]},
  ],{height:200,fmt:fmt.pct});

  /* ---- rough vol scaling fan ---- */
  $('sub-rough').textContent=`m(q,Δ) scaling of SPY GK log-vol: slope of each line = ζ(q); H = ζ(q)/q. `+
    `H=${rough.daily.H.toFixed(3)} CI [${rough.daily.ci.ci_lo.toFixed(2)},${rough.daily.ci.ci_hi.toFixed(2)}]`;
  const qcolors=[COL.cyan,COL.green,COL.amber,COL.orange,COL.rose];
  const logd=rough.daily.deltas.map(Math.log);
  XYChart('ch-rough',rough.daily.qs.map((q,i)=>({
    name:'q='+q, x:logd, y:rough.daily.log_m[i], color:qcolors[i], points:true, width:1.2,
  })),{height:260,xfmt:v=>'Δ='+Math.exp(v).toFixed(0),yfmt:v=>v.toFixed(1),xlabel:'log Δ (days)'});
  $('sub-rough2').textContent=`Cross-section: median H=${rough.cross_sectional.median_H.toFixed(2)} `+
    `(IQR ${rough.cross_sectional.q25.toFixed(2)}–${rough.cross_sectional.q75.toFixed(2)}, ${rough.cross_sectional.n_names} names). `+
    `5d-smoothed H=${rough.smoothed_5d.H.toFixed(2)} — smoothing biases up, noise biases down; truth sits between. Subwindow H: `+
    rough.subwindow_H.map(x=>x.toFixed(2)).join(', ');

  /* ---- MP spectrum ---- */
  const sp=rmt.spectrum;
  $('sub-rmt').textContent=`final 252d window: ${sp.n_signal} eigenvalues above the MP edge (${sp.edge.toFixed(2)}); `+
    `market mode λ₁=${sp.eigvals[0].toFixed(1)} (off scale)`;
  const bulk=sp.eigvals.filter(v=>v<3.0);
  const bins=24, bw=3.0/bins, hist=new Array(bins).fill(0);
  for(const v of bulk) hist[Math.min(bins-1,Math.floor(v/bw))]+=1/(bulk.length*bw)/1.4;
  XYChart('ch-mp',[
    {x:hist.map((_,i)=>(i+0.5)*bw),y:hist,color:'#27d3ee55',bars:true,binw:bw,name:'empirical'},
    {name:'MP density',x:sp.mp_grid,y:sp.mp_pdf,color:COL.rose,width:1.8},
  ],{height:220,y0:0,xfmt:v=>v.toFixed(1),yfmt:v=>v.toFixed(1),xlabel:'eigenvalue'});
  let hr='<tr><th>Estimator</th><th>Min-var realized vol</th><th>Turnover/yr</th></tr>';
  const rmtNames={sample:'Sample (EWMA)',lw:'Ledoit-Wolf',rmt:'RMT denoised',lw_rmt:'LW + RMT'};
  const bestRmt=Object.entries(rmt.methods).sort((a,b)=>a[1].realized_vol-b[1].realized_vol)[0][0];
  for(const [m,v] of Object.entries(rmt.methods))
    hr+=`<tr><td${m===bestRmt?' style="color:var(--cyan)"':''}>${rmtNames[m]}${m===bestRmt?' ★':''}</td><td>${pct(v.realized_vol)}</td><td>${v.turnover_per_year.toFixed(1)}×</td></tr>`;
  $('tbl-rmt').innerHTML=hr;

  /* ---- CVaR table + statarb ---- */
  let hc='<tr><th>Engine</th><th>Sharpe</th><th>CVaR95</th><th>MaxDD</th><th>Turnover</th></tr>';
  const cvNames={hrp:'HRP',cvar_hist:'Min-CVaR (hist)',cvar_ewma:'Min-CVaR (EWMA)',cvar_regime:'Min-CVaR (regime)'};
  for(const [e,v] of Object.entries(cvar))
    hc+=`<tr><td>${cvNames[e]||e}</td><td>${v.sharpe.toFixed(2)}</td><td>${pct(v.cvar95)}</td>
      <td>${pct(v.max_dd)}</td><td>${v.turnover_per_year.toFixed(1)}×</td></tr>`;
  $('tbl-cvar').innerHTML=hc;

  $('sub-statarb').textContent=`avg ${sa.n_open_mean.toFixed(1)} open positions · ${sa.m_factors_median.toFixed(0)} PCA factors (MP edge) · `+
    `full ${(sa.full.ann_ret*100).toFixed(1)}%/yr (SR ${sa.full.sharpe.toFixed(2)}) · pre-2019 SR ${sa.pre2019.sharpe.toFixed(2)} · post-2019 SR ${sa.post2019.sharpe.toFixed(2)}`;
  new LineChart('ch-statarb',[
    {name:'stat-arb NAV (gross sleeve)',dates:sa.nav.dates,values:sa.nav.values,color:COL.violet,width:1.6},
  ],{height:180,fmt:fmt.nav});

  /* ---- ensemble ---- */
  $('sub-ens').textContent=`All blends of the three signal sleeves tie (best static ${ens.best_static_sharpe.toFixed(2)}): `+
    `the HRP+BL backbone dominates the result, so blend weights are nearly irrelevant — itself a finding.`;
  const wr=ens.weights_river;
  new StackedArea('ch-river',wr.dates,[
    {name:'momentum',values:wr.momentum,color:COL.blue},
    {name:'mean reversion',values:wr.mean_reversion,color:COL.amber},
    {name:'low vol',values:wr.low_vol,color:COL.green},
  ],{height:220});
  new LineChart('ch-regret',[
    {name:'fixed-share',dates:ens.regret.dates,values:ens.regret.fixed_share,color:COL.cyan,width:1.6},
    {name:'hedge',dates:ens.regret.dates,values:ens.regret.hedge,color:COL.amber,width:1.2,dash:[4,3]},
  ],{height:220,fmt:fmt.num});
  let he='<tr><th>Method</th><th>Sharpe</th></tr>';
  for(const [m,v] of Object.entries(ens.methods))
    he+=`<tr><td>${m.replace('_',' ')}</td><td>${v.sharpe.toFixed(2)}</td></tr>`;
  $('tbl-ens').innerHTML=he;

  /* ---- forensics ---- */
  $('sub-forensics').textContent=`Trial ledger N=${forz.n_trials} configurations (variant family + every sweep this project ever ran). `+
    `Validated on known-overfit worlds before being pointed at ourselves.`;
  const fcards=[
    {k:'Deflated Sharpe',v:forz.dsr.dsr.toFixed(2),s:`SR ${forz.dsr.sr_annual.toFixed(2)} vs E[max noise] ${forz.dsr.sr0_annual.toFixed(2)}`},
    {k:'PBO',v:forz.pbo.pbo.toFixed(2),s:`${forz.pbo.n_combos} CSCV splits, ${forz.pbo.n_variants} variants`},
    {k:'Sharpe 95% CI',v:`[${forz.bootstrap.ci_lo.toFixed(2)}, ${forz.bootstrap.ci_hi.toFixed(2)}]`,s:'stationary bootstrap'},
    {k:'P(SR ≤ 0)',v:(forz.bootstrap.p_sr_below_0*100).toFixed(1)+'%',s:'2000 resamples'},
  ];
  for(const it of fcards){
    const d=document.createElement('div');d.className='greek';
    d.innerHTML=`<div class="k">${it.k}</div><div class="g mono neu">${it.v}</div><div class="s">${it.s}</div>`;
    $('forensic-cards').appendChild(d);}
  const le=forz.pbo_logits_edges, lc=forz.pbo_logits_hist;
  XYChart('ch-pbo',[
    {x:lc.map((_,i)=>(le[i]+le[i+1])/2),y:lc,color:'#a78bfa88',bars:true,
     binw:le[1]-le[0],name:'logit(OOS rank of IS winner)'},
  ],{height:200,y0:0,xfmt:v=>v.toFixed(1),yfmt:v=>v.toFixed(0),xlabel:'logit (negative = overfit)'});

  const fan=forz.fan;
  new LineChart('ch-fan',[
    {name:'p95',dates:fan.dates,values:fan.p95,color:'#27d3ee00',width:0.1},
    {name:'p75',dates:fan.dates,values:fan.p75,color:'#27d3ee00',width:0.1},
    {name:'median',dates:fan.dates,values:fan.p50,color:COL.cyan,width:1.8},
    {name:'p25',dates:fan.dates,values:fan.p25,color:'#27d3ee00',width:0.1},
    {name:'p5',dates:fan.dates,values:fan.p5,color:'#27d3ee00',width:0.1},
  ],{height:240,fmt:fmt.nav,bands:[{u:0,l:4,color:'#27d3ee14'},{u:1,l:3,color:'#27d3ee22'}]});

  /* ---- X²: tails study ---- */
  if(R.tails){
    $('panel-tails').style.display='';
    const TL=R.tails, mc=TL.mc, rd=TL.real;
    let hm='<tr><th>World (true K=3)</th><th>Family</th>'+
      mc.Ks.map(k=>`<th>K=${k}</th>`).join('')+'<th>overfit</th></tr>';
    for(const [w,lab] of [["gaussian_world","Gaussian world"],["fat_world","Fat-tail world (t₅)"]]){
      for(const f of ["gauss","t"]){
        const cK=mc[w].chosen_K[f];
        hm+=`<tr><td>${f==='gauss'?lab:''}</td><td>${f==='gauss'?'Gaussian':'Student-t'}</td>`+
          mc.Ks.map(k=>`<td>${cK[String(k)]}</td>`).join('')+
          `<td class="${mc[w].frac_overfit[f]>0.6?'neg':'pos'}">${(mc[w].frac_overfit[f]*100).toFixed(0)}%</td></tr>`;}}
    $('tbl-mc').innerHTML=hm;
    $('sub-mc').textContent=`${mc.n_seeds} seeds/world, selection by held-out predictive log-score over K=2..5. `+
      `Fat tails push the Gaussian family to maximal K; the t family is largely immune.`;

    const Ks=[2,3,4,5];
    XYChart('ch-tcurve',[
      {name:'Gaussian',x:Ks,y:Ks.map(k=>rd.logscores_eval['G'+k]),color:COL.rose,points:true},
      {name:'Student-t',x:Ks,y:Ks.map(k=>rd.logscores_eval['T'+k]),color:COL.cyan,points:true},
    ],{height:230,xfmt:v=>Math.abs(v-Math.round(v))<1e-9?'K='+v.toFixed(0):'',
       yfmt:v=>v.toFixed(3)});

    let ha='<tr><th>Comparison</th><th>AG stat</th><th>p</th><th>verdict</th></tr>';
    const aglab={T3_vs_G3:'t-HMM-3 vs Gaussian-3',T3_vs_G5:'t-HMM-3 vs Gaussian-5',
      G5_vs_G3:'Gaussian-5 vs Gaussian-3',T3_vs_SJM3:'t-HMM-3 vs SJM-3',
      T5_vs_T3:'t-HMM-5 vs t-HMM-3',T3_vs_Dur3x3:'t-HMM-3 vs DurHMM'};
    for(const [k,v] of Object.entries(rd.ag)){
      const sig=v.p<0.05?'<span class="pos">significant</span>':
        v.p<0.10?'<span class="verdict-mixed">marginal</span>':'tie';
      ha+=`<tr><td>${aglab[k]||k}</td><td>${v.stat>=0?'+':''}${v.stat.toFixed(2)}</td>
        <td>${v.p.toFixed(3)}</td><td>${sig}</td></tr>`;}
    $('tbl-ag').innerHTML=ha;

    let hs3='<tr><th>Model</th><th>log-score</th><th>in MCS?</th></tr>';
    const order=Object.entries(rd.logscores_eval).sort((a,b)=>b[1]-a[1]);
    for(const [m,s] of order){
      const inSet=rd.mcs.mcs.includes(m);
      hs3+=`<tr><td${m===rd.mcs.best?' style="color:var(--cyan)"':''}>${m}${m===rd.mcs.best?' ★':''}</td>
        <td>${s.toFixed(4)}</td><td>${inSet?'<span class="pos">yes</span>':'<span class="neg">eliminated</span>'}</td></tr>`;}
    $('tbl-mcs').innerHTML=hs3;
    $('sub-nus').textContent=`Market per-state ν (t-HMM K=3, full fit): Bull ${rd.market_nus_K3[0]}, `+
      `Volatile ${rd.market_nus_K3[1]}, Bear ${rd.market_nus_K3[2]} — the volatile state carries the tails; `+
      `the bear state is high-variance but near-Gaussian.`;
  }

  /* ---- X²: RFSV panel ---- */
  if(R.rfsv){
    $('panel-rfsv').style.display='';
    const RF=R.rfsv;
    $('sub-rfsv').textContent=`Fractional-kernel forecaster (walk-forward H, EWMA noise filter hl=${RF.kernel.halflife}, `+
      `calibration b=${RF.kernel.calib_b.toFixed(2)}) vs the vol lab, ${RF.n_oos_days} OOS days.`;
    let hf='<tr><th>Forecaster</th><th>QLIKE</th><th>AG vs RFSV</th><th>in MCS?</th></tr>';
    for(const m of ['har','garch','rfsv','ewma']){
      const ag=m==='rfsv'?null:RF.ag[`rfsv_vs_${m}`];
      const inSet=RF.mcs.mcs.includes(m);
      hf+=`<tr><td${m===RF.winner?' style="color:var(--cyan)"':''}>${m.toUpperCase()}${m===RF.winner?' ★':''}</td>
        <td>${RF.qlike[m].toFixed(4)}</td>
        <td>${ag?(ag.stat>=0?'+':'')+ag.stat.toFixed(2)+' (p='+ag.p.toFixed(3)+')':'—'}</td>
        <td>${inSet?'<span class="pos">yes</span>':'<span class="neg">eliminated</span>'}</td></tr>`;}
    $('tbl-rfsv').innerHTML=hf;
  }

  /* ---- LAWS panel ---- */
  if(R.laws){
    $('panel-laws').style.display='';
    const L=R.laws;
    // L1 scatter: per-asset raw kurt vs deformed kurt
    const pa=L.l1.per_asset;
    const names=Object.keys(pa);
    XYChart('ch-l1',[
      {name:'kurt: raw → deformed', x:names.map(n=>Math.log10(pa[n].kurt_raw)),
       y:names.map(n=>pa[n].kurt_z), color:COL.cyan, points:true, width:0.001},
      {name:'Gaussian (3)', x:[Math.log10(3),Math.log10(60)], y:[3,3],
       color:COL.green, dash:[4,3], width:1.2},
    ],{height:240,xfmt:v=>(10**v).toFixed(0),yfmt:v=>v.toFixed(1),
       xlabel:'raw kurtosis (log scale)'});
    $('sub-l1').textContent=`Every dot is an asset: x = raw kurtosis, y = kurtosis after `+
      `dividing by realized vol (smooth=${L.l1.best_smooth}). All 48 land near the Gaussian line. `+
      `Cross-asset KS / sampling floor = ${L.l1.collapse.ratio.toFixed(2)}.`;
    let hp='<tr><th>Diagnostic</th><th>raw returns</th><th>deformed returns</th></tr>';
    hp+=`<tr><td>Gaussian K-rise (3→5), nats/day</td><td>+${L.l1.k_rise_raw.toFixed(4)}</td>
      <td class="pos">${L.l1.k_rise_z>=0?'+':''}${L.l1.k_rise_z.toFixed(4)}</td></tr>`;
    hp+=`<tr><td>t-HMM per-state ν</td><td>16.8 / 3.7 / 300</td>
      <td class="pos">${L.l1.nus_z_hmm.join(' / ')}</td></tr>`;
    hp+=`<tr><td>median kurtosis (48 assets)</td><td>${L.l1.median_kurt_raw.toFixed(1)}</td>
      <td class="pos">${L.l1.median_kurt_z.toFixed(2)}</td></tr>`;
    $('tbl-p1b').innerHTML=hp;
    let hl23='<tr><th>Screen</th><th>Statistic</th><th>Verdict</th></tr>';
    hl23+=`<tr><td>L2 parameter-free kurtosis law</td>
      <td>log-corr ${L.l2.log_corr.toFixed(2)}, excess +${L.l2.median_excess.toFixed(1)}</td>
      <td><span class="neg">killed</span> — kurtosis is mostly day-specific (jumps), not slow SV</td></tr>`;
    hl23+=`<tr><td>L3 multifractal universality</td>
      <td>λ² ${L.l3.median.toFixed(3)} IQR [${L.l3.iqr[0].toFixed(3)}, ${L.l3.iqr[1].toFixed(3)}]</td>
      <td><span class="verdict-mixed">survived</span> — tight cross-asset clustering, tail-confound caveat</td></tr>`;
    $('tbl-l23').innerHTML=hl23;
  }

  /* ---- CLOCK panel ---- */
  if(R.clock){
    $('panel-clock').style.display='';
    const C=R.clock, vs=C.versions;
    const labels=['raw','same_day','lagged'];
    const disp={'raw':'raw returns','same_day':'÷ same-day clock','lagged':'÷ lagged clock'};
    // grouped bar chart via XYChart bars: fraction of pairs above null
    XYChart('ch-clock',[
      {name:'all pairs',x:[0,1,2],y:labels.map(l=>vs[l].all.q50.frac_above95),
       color:'#27d3ee99',bars:true,binw:0.28},
      {name:'equity pairs',x:[0.32,1.32,2.32],y:labels.map(l=>vs[l].equities.q50.frac_above95),
       color:'#fb718599',bars:true,binw:0.28},
      {name:'null rate (5%)',x:[-0.3,2.7],y:[0.05,0.05],color:COL.green,dash:[4,3],width:1.2},
    ],{height:240,y0:0,xfmt:v=>({0:'raw',1:'÷ same-day',2:'÷ lagged'})[Math.round(v)]||'',
       yfmt:v=>(v*100).toFixed(0)+'%',xlabel:'fraction of pairs above their Gaussian-null 95% band (q=5%)'});
    let hc2='<tr><th>Version</th><th>frac &gt; null 95% (all)</th><th>median excess λ(5%)</th><th>equities</th></tr>';
    for(const l of labels)
      hc2+=`<tr><td>${disp[l]}</td><td>${(vs[l].all.q50.frac_above95*100).toFixed(0)}%</td>
        <td>${vs[l].all.q50.median_excess>=0?'+':''}${vs[l].all.q50.median_excess.toFixed(3)}</td>
        <td>${(vs[l].equities.q50.frac_above95*100).toFixed(0)}%</td></tr>`;
    $('tbl-clock').innerHTML=hc2;
    $('sub-clock').textContent=`Decomposition: clocks explain `+
      `${(100*(1-vs.same_day.all.q50.median_excess/vs.raw.all.q50.median_excess)).toFixed(0)}% of the raw joint-tail excess; `+
      `${(100*vs.lagged.all.q50.median_excess/vs.raw.all.q50.median_excess).toFixed(0)}% of it is unpredictable common clock surges. `+
      `Vol-clock commonality: first factor = ${(C.c3.eig1_share*100).toFixed(0)}% of log-vol correlation. `+
      `The market clock alone removes ${(C.c3.mkt_clock_share_other*100).toFixed(0)}% of non-equity kurtosis but `+
      `${(C.c3.mkt_clock_share_equities*100).toFixed(0)}% for single stocks — idiosyncratic clocks matter for names, not for asset classes.`;
  }

  /* ---- SURGE panel ---- */
  if(R.surge){
    $('panel-surge').style.display='';
    const S=R.surge;
    const taus=Array.from({length:40},(_,i)=>i+1);
    const kcol={SPY:COL.cyan, GLD:COL.amber, TLT:COL.violet, AAPL:COL.rose};
    XYChart('ch-lev',Object.entries(S.s2.kernels).map(([c,k])=>({
      name:c, x:taus, y:k, color:kcol[c]||COL.dim, width:1.6,
    })).concat([{name:'',x:[1,40],y:[0,0],color:'#3d4d68',dash:[4,3],width:1}]),
    {height:250,xfmt:v=>'τ='+v.toFixed(0),yfmt:v=>v.toFixed(2)});
    let hs='<tr><th>Question</th><th>Statistic</th><th>Verdict</th></tr>';
    hs+=`<tr><td>S1: clock has a clock?</td>
      <td>kurt(u) ${S.s1.median_kurt_u.toFixed(1)}, AC₁|u| ${S.s1.median_ac1.toFixed(2)}, meta-deformed ${S.s1.median_kurt_z2.toFixed(1)}</td>
      <td><span class="verdict-mixed">clusters, but no recursion</span></td></tr>`;
    hs+=`<tr><td>S2: arrow of time</td>
      <td>median Z ${S.s2.median_z>=0?'+':''}${S.s2.median_z.toFixed(2)}, ${(S.s2.frac_significant_pos*100).toFixed(0)}% sig.</td>
      <td><span class="verdict-mixed">faint in daily bars</span></td></tr>`;
    hs+=`<tr><td>S3: surge intensity forecastable?</td>
      <td>lift ${S.s3.lift.toFixed(2)} CI [${S.s3.ci_lo.toFixed(2)}, ${S.s3.ci_hi.toFixed(2)}]</td>
      <td><span class="verdict-mixed">suggestive, not significant</span></td></tr>`;
    $('tbl-surge').innerHTML=hs;
  }

  /* ---- BITS panel ---- */
  if(R.bits){
    $('panel-bits').style.display='';
    const B=R.bits;
    let hb='<tr><th>Channel</th><th>bits/day</th><th>signif.</th><th>era pre/post 2018</th></tr>';
    hb+=`<tr><td>direction, h=1 (SPY)</td><td>${B.direction["1"].bits_net.toFixed(5)}</td>
      <td>${B.direction["1"].significant?'<span class="pos">yes</span>':'<span class="neg">no</span>'}</td>
      <td>${B.eras.direction.pre.toFixed(4)} / ${B.eras.direction.post.toFixed(4)}</td></tr>`;
    hb+=`<tr><td>direction, h=5</td><td>${B.direction["5"].bits_net.toFixed(5)}</td>
      <td>${B.direction["5"].significant?'<span class="pos">yes</span>':'no'}</td><td>—</td></tr>`;
    hb+=`<tr><td>direction, h=21</td><td>${B.direction["21"].bits_net.toFixed(5)}</td>
      <td>${B.direction["21"].significant?'<span class="pos">yes</span>':'no'}</td><td>—</td></tr>`;
    hb+=`<tr><td>direction, cross-asset median</td><td>${B.direction_cross.median_bits.toFixed(5)}</td>
      <td>${B.direction_cross.n_sig}/${B.direction_cross.n_assets} assets</td><td>—</td></tr>`;
    hb+=`<tr><td><b>magnitude (vol), SPY</b></td><td><b>${B.magnitude.spy_bits.toFixed(3)}</b></td>
      <td><span class="pos">yes</span></td>
      <td>${B.eras.magnitude.pre.toFixed(3)} / ${B.eras.magnitude.post.toFixed(3)}</td></tr>`;
    hb+=`<tr><td>magnitude, cross-asset median</td><td>${B.magnitude.cross_median_bits.toFixed(3)}</td>
      <td><span class="pos">yes</span></td><td>—</td></tr>`;
    hb+=`<tr><td>total next-day return (SPY)</td><td>${B.total_bits.toFixed(3)}</td>
      <td><span class="pos">yes</span></td><td>—</td></tr>`;
    $('tbl-bits').innerHTML=hb;
    let hc='<tr><th>Quantity</th><th>Value</th></tr>';
    hc+=`<tr><td>direction-only Sharpe ceiling (h=1)</td><td>${B.ceilings.direction_sr.toFixed(2)}</td></tr>`;
    hc+=`<tr><td>return-channel Gaussian ceiling</td><td>${B.ceilings.total_sr.toFixed(1)}</td></tr>`;
    hc+=`<tr><td>vol-channel SR-equivalent</td><td>${B.ceilings.vol_channel_sr.toFixed(1)}</td></tr>`;
    hc+=`<tr><td>KRONOS bits consumed (SR ${B.utilization.kronos_sr.toFixed(2)})</td><td>${B.utilization.kronos_bits.toFixed(4)} bits/day</td></tr>`;
    $('tbl-ceil').innerHTML=hc;
    $('sub-bits').textContent=`Reading: the return-channel and vol-channel ceilings are dominated by `+
      `MAGNITUDE information — monetizable through vol instruments and vol-targeting, not directional bets. `+
      `KRONOS's realized Sharpe consumes ~${B.utilization.kronos_bits.toFixed(3)} bits/day, between the h=1 `+
      `direction budget (${B.direction["1"].bits_net.toFixed(4)}) and the h=21 budget (${B.direction["21"].bits_net.toFixed(3)}) — `+
      `consistent with its edge coming from slow regime/momentum tilts plus vol-targeting (the magnitude channel), not daily timing. `+
      `Caveat: bounds are conditional on our feature set; they lower-bound the true I against all public information.`;
    if(R.arrow){
      const A=R.arrow;
      let ha2='<tr><th>Series</th><th>assets w/ arrow (sig 5%)</th><th>median net EP (bits)</th><th>SPY</th></tr>';
      const lab={returns:'raw returns', clock:'vol clock (weekly innov.)', deformed:'deformed returns'};
      for(const k of ['returns','clock','deformed'])
        ha2+=`<tr><td>${lab[k]}</td><td>${A.summary[k].n_sig}/48</td>
          <td>${A.summary[k].median_net_bits.toFixed(5)}</td>
          <td>${A.spy[k].ep.toFixed(4)}${A.spy[k].sig?' <span class="pos">sig</span>':''}</td></tr>`;
      $('tbl-ceil').innerHTML += `<tr><td colspan="2" style="padding-top:14px;color:var(--dim);
        font-size:10.5px;letter-spacing:1.5px">ENTROPY PRODUCTION — TIME'S ARROW</td></tr>`;
      $('tbl-ceil').innerHTML += ha2;
    }
  }

  /* ---- DECATHLON panel ---- */
  if(R.decathlon){
    $('panel-decathlon').style.display='';
    const D=R.decathlon;
    const evs=Object.keys(D.spy.events);
    const evShort=evs.map(e=>e.split('_')[0]);
    const evTitle={E1_efficiency:'efficiency',E2_fat_tails:'fat tails',
      E3_clustering:'vol clustering',E4_long_memory:'long-memory clock',
      E5_leverage:'leverage effect',E6_one_clock:'one-clock',
      E7_clock_jumps:'clock jumps up',E8_arrow:'arrow in coupling',
      E9_no_sign_info:'no sign info',E10_tail_asym:'crash asymmetry'};
    let h='<tr><th>Config</th>'+evs.map((e,i)=>`<th title="${evTitle[e]}">${evShort[i]}</th>`).join('')+'<th>score</th></tr>';
    const rows=Object.entries(D.configs).concat([["SPY (real)",{events:D.spy.events,score:D.spy.score}]]);
    for(const [name,rec] of rows){
      h+=`<tr><td${name.startsWith('SPY')?' style="color:var(--cyan)"':''}>${name}</td>`;
      for(const e of evs){
        const v=rec.events[e];
        h+=`<td>${v?'<span class="pos">●</span>':'<span style="color:#2a3850">○</span>'}</td>`;}
      h+=`<td><b>${rec.score}/10</b></td></tr>`;}
    $('tbl-deca').innerHTML=h;
    $('sub-deca').textContent=`Ingredients: F fundamentalists · C chartists · V vol-targeters · `+
      `M market makers · H multi-horizon cohorts. Reading the ladder: the Gaussian events `+
      `(E1, E6, E9) come free; the vol-targeting spiral buys the wild events (E2, E5, E7, E10) at the `+
      `cost of leaking momentum; market makers buy efficiency back (E1) — efficiency and wildness are `+
      `contributed by DIFFERENT agents. What no flow buys: long memory (E3 slow-decay, E4), the arrow in `+
      `the coupling (E8), and information-free signs in V-configs (E9) — mechanical flows leak forecastable `+
      `structure that real markets price away. The minimal market's missing organ is expectation.`;
  }

  /* ---- CRITICAL panel ---- */
  if(R.critical){
    $('panel-critical').style.display='';
    const C=R.critical;
    const sigs=['phi','ac1_x','spectral','skew_dx'];
    const sigName={phi:'φ (AR1)',ac1_x:'AC1(x)',spectral:'spectral',skew_dx:'skew'};
    // grouped bars: real vs fold precursor shift
    XYChart('ch-precursor',[
      {name:'real markets',x:sigs.map((_,i)=>i),y:sigs.map(s=>C.precursor.real[s]),
       color:'#27d3ee99',bars:true,binw:0.34},
      {name:'fold bifurcation',x:sigs.map((_,i)=>i+0.38),y:sigs.map(s=>C.precursor.fold[s]),
       color:'#fb718599',bars:true,binw:0.34},
      {name:'',x:[-0.3,3.7],y:[0,0],color:'#3d4d68',width:1},
    ],{height:230,y0:-0.2,
       xfmt:v=>Math.abs(v-Math.round(v))<0.15?(sigName[sigs[Math.round(v)]]||''):'',
       yfmt:v=>v.toFixed(1),xlabel:'pre-crash shift (std units)'});
    $('sub-crit2').textContent=`Every critical-slowing-down indicator rises far more before a known `+
      `fold bifurcation (rose) than before real crashes (cyan). The real φ precursor (+${C.precursor.real.phi.toFixed(2)} std) `+
      `is an order of magnitude below the bifurcation's (+${C.precursor.fold.phi.toFixed(2)}) — a vestigial, non-exploitable signature.`;
    let h='<tr><th>Quantity</th><th>Value</th></tr>';
    h+=`<tr><td>verdict</td><td><b>${C.verdict.replace(/_/g,' ')}</b></td></tr>`;
    h+=`<tr><td>median incremental AUC (48 assets)</td><td>${C.median_gain>=0?'+':''}${C.median_gain.toFixed(4)}</td></tr>`;
    h+=`<tr><td>fraction of assets positive</td><td>${(C.frac_pos*100).toFixed(0)}% (sign-test p=${C.sign_test_p.toFixed(2)})</td></tr>`;
    h+=`<tr><td>equity mean gain</td><td>+${C.equity_mean_gain.toFixed(4)} [${C.equity_ci[0].toFixed(4)}, ${C.equity_ci[1].toFixed(4)}]</td></tr>`;
    h+=`<tr><td colspan="2" style="padding-top:12px;color:var(--dim);font-size:10.5px;letter-spacing:1.5px">GATE: METHOD CONVICTS &amp; EXONERATES</td></tr>`;
    h+=`<tr><td>synthetic fold bifurcation</td><td class="pos">+${C.gate.fold_gain.toFixed(2)} AUC gain (detected)</td></tr>`;
    h+=`<tr><td>synthetic shock process</td><td>+${C.gate.shock_gain.toFixed(2)} AUC gain (exonerated)</td></tr>`;
    h+=`<tr><td colspan="2" style="padding-top:12px;color:var(--dim);font-size:10.5px;letter-spacing:1.5px">ROBUSTNESS</td></tr>`;
    h+=`<tr><td>horizon sweep (eq median gain)</td><td>H10 ${C.hsweep["10"].median.toFixed(3)} · H20 ${C.hsweep["20"].median.toFixed(3)} · H60 ${C.hsweep["60"].median.toFixed(3)}</td></tr>`;
    h+=`<tr><td>down-crash vs up-spike (eq median)</td><td>${C.asymmetry.down.toFixed(4)} vs ${C.asymmetry.up.toFixed(4)}</td></tr>`;
    $('tbl-critical').innerHTML=h;
    const cl=C.classes;
    $('sub-crit').textContent=`Universality (median gain by class): `+
      Object.entries(cl).map(([k,v])=>`${k.replace('_',' ')} ${v.median_gain>=0?'+':''}${v.median_gain.toFixed(3)}`).join(' · ')+
      `. No asset class shows a robust signal; the only faintly-positive cells (equity indices, H=60) are not significant. The pipeline is NOT underpowered — it recovers the fold's +${C.gate.fold_gain.toFixed(2)} gain and +${C.precursor.fold.phi.toFixed(2)}-std precursor. Conclusion: market crashes are statistically closer to shocks than to bifurcations.`;
  }

  /* ---- REFLEX panel ---- */
  if(R.reflex){
    $('panel-reflex').style.display='';
    const X=R.reflex;
    // headline bars: raw, deformed, SV-null, with the near-critical line
    XYChart('ch-reflex',[
      {name:'',x:[0],y:[X.median_n_raw],color:'#fb718599',bars:true,binw:0.6},
      {name:'',x:[1],y:[X.median_n_def],color:'#27d3ee99',bars:true,binw:0.6},
      {name:'',x:[2],y:[X.sv_null_n_def],color:'#7d8ca366',bars:true,binw:0.6},
      {name:'near-critical (n=1)',x:[-0.5,2.5],y:[1,1],color:COL.amber,dash:[4,3],width:1},
    ],{height:230,y0:0,yMax:1.05,
       xfmt:v=>Math.abs(v-Math.round(v))<0.15?({0:'raw',1:'÷ vol clock',2:'no-excite null'})[Math.round(v)]||'':'',
       yfmt:v=>v.toFixed(1),xlabel:'Hawkes branching ratio n'});
    $('sub-reflex2').textContent=`Raw extreme-return events look near-critical (n=${X.median_n_raw.toFixed(2)}); `+
      `vol-clock-adjusted events collapse to n=${X.median_n_def.toFixed(2)}, sitting at the `+
      `no-self-excitation null (${X.sv_null_n_def.toFixed(2)}). The near-criticality is volatility clustering.`;
    let h='<tr><th>Quantity</th><th>Value</th></tr>';
    h+=`<tr><td>raw branching ratio (median, 48 assets)</td><td>${X.median_n_raw.toFixed(3)} [${X.ci_raw[0].toFixed(2)}, ${X.ci_raw[1].toFixed(2)}]</td></tr>`;
    h+=`<tr><td>deformed branching ratio</td><td class="neu">${X.median_n_def.toFixed(3)} [${X.ci_def[0].toFixed(2)}, ${X.ci_def[1].toFixed(2)}]</td></tr>`;
    h+=`<tr><td>clustering share of endogeneity</td><td><b>${(X.clustering_share*100).toFixed(0)}%</b></td></tr>`;
    h+=`<tr><td>no-self-excitation null (deformed)</td><td>${X.sv_null_n_def.toFixed(3)}</td></tr>`;
    h+=`<tr><td>SPY</td><td>raw ${X.spy.n_raw.toFixed(2)} → deformed ${X.spy.n_def.toFixed(2)}</td></tr>`;
    h+=`<tr><td colspan="2" style="padding-top:12px;color:var(--dim);font-size:10.5px;letter-spacing:1.5px">DID REFLEXIVITY GROW? (PRE/POST 2018)</td></tr>`;
    h+=`<tr><td>raw n</td><td>${X.trend.pre.n_raw.toFixed(3)} → ${X.trend.post.n_raw.toFixed(3)}</td></tr>`;
    h+=`<tr><td>deformed n</td><td>${X.trend.pre.n_def.toFixed(3)} → ${X.trend.post.n_def.toFixed(3)} (fell)</td></tr>`;
    h+=`<tr><td colspan="2" style="padding-top:12px;color:var(--dim);font-size:10.5px;letter-spacing:1.5px">SYSTEMIC vs IDIOSYNCRATIC · BRIDGE TO CRITICAL</td></tr>`;
    h+=`<tr><td>systemic surprise n</td><td>${X.systemic.n.toFixed(3)} vs single-asset ${X.systemic.median_single.toFixed(3)}</td></tr>`;
    if(X.f5) h+=`<tr><td>corr(n_raw, CSD φ-shift)</td><td>${X.f5.corr_nraw_phishift>=0?'+':''}${X.f5.corr_nraw_phishift.toFixed(2)} (null)</td></tr>`;
    $('tbl-reflex').innerHTML=h;
  }

  /* ---- CONSTANTS panel ---- */
  if(R.constants){
    $('panel-constants').style.display='';
    const K=R.constants, Q=K.quantities;
    const clsColor={CONSTANT:'pos','REGIME-VARYING':'verdict-mixed',DRIFTING:'neg'};
    let h='<tr><th>Market law</th>'+K.eras.map(e=>`<th>${e}</th>`).join('')+'<th>verdict</th></tr>';
    for(const [q,r] of Object.entries(Q)){
      h+=`<tr><td>${r.name}</td>`+
        r.era_values.map(v=>`<td>${v}</td>`).join('')+
        `<td><span class="${clsColor[r.class]||''}">${r.class}</span></td></tr>`;}
    $('tbl-constants').innerHTML=h;
    const consts=Object.values(Q).filter(r=>r.class==='CONSTANT').map(r=>r.name);
    const reg=Object.values(Q).filter(r=>r.class==='REGIME-VARYING').map(r=>r.name);
    const drift=Object.values(Q).filter(r=>r.class==='DRIFTING').map(r=>r.name);
    $('sub-constants').innerHTML=`<b style="color:var(--green)">Constants of the market:</b> `+
      consts.join(', ')+`. <b style="color:var(--amber)">Regime-varying (crisis-driven, no trend):</b> `+
      reg.join(', ')+`. <b style="color:var(--rose)">Secular drift:</b> `+(drift.join(', ')||'none')+
      `. The one-clock collapse stays in [3.2, 3.7] every era while raw kurtosis ranges [5.6, 12.2] — the deformation LAW holds always. No support for secular market evolution; the structure is fixed and only crisis intensity moves.`;
  }

  /* ---- TRADE panel ---- */
  if(R.trade){
    $('panel-trade').style.display='';
    const T=R.trade;
    new LineChart('ch-trade',[
      {name:'KRONOS-TRADE',dates:T.nav.trade.dates,values:T.nav.trade.values,color:COL.cyan,width:2},
      {name:'realized-vol control',dates:T.nav.realized.dates,values:T.nav.realized.values,color:COL.violet,width:1,dash:[4,3]},
      {name:'SPY',dates:T.nav.spy.dates,values:T.nav.spy.values,color:COL.dim,width:1.2},
      {name:'equal-weight',dates:T.nav.ew.dates,values:T.nav.ew.values,color:COL.orange,width:1,dash:[2,3]},
    ],{height:300,fmt:fmt.nav,regimeBands:true});
    let h='<tr><th>Strategy</th><th>CAGR</th><th>Sharpe</th><th>MaxDD</th><th>CVaR95</th></tr>';
    for(const [nm,s] of Object.entries(T.metrics))
      h+=`<tr><td${nm.startsWith('KRONOS')?' style="color:var(--cyan)"':''}>${nm}</td>
        <td>${(s.cagr*100).toFixed(1)}%</td><td>${s.sharpe.toFixed(2)}</td>
        <td>${(s.max_dd*100).toFixed(0)}%</td><td>${(s.cvar95*100).toFixed(2)}%</td></tr>`;
    $('tbl-trade').innerHTML=h;
    const rec=T.recommendation;
    let hr='<tr><th>Ticker</th><th>Weight</th><th>$ / 100k</th></tr>';
    const tw=Object.entries(rec.target_weights).slice(0,12);
    for(const [tk,w] of tw)
      hr+=`<tr><td>${tk}</td><td>${(w*100).toFixed(1)}%</td><td>${(rec.dollar_alloc[tk]||0).toLocaleString()}</td></tr>`;
    hr+=`<tr><td>CASH</td><td></td><td>${Math.round(rec.cash).toLocaleString()}</td></tr>`;
    $('tbl-rec').innerHTML=hr;
    $('sub-rec').textContent=`As of ${rec.as_of} · regime ${rec.regime} · forecast vol `+
      `${(rec.forecast_portfolio_vol_ann*100).toFixed(1)}% · exposure ${(rec.exposure*100).toFixed(0)}% `+
      `· no leverage by design. Risk-managed, mechanically de-risked (crashes are unforecastable — CRITICAL).`;
  }

  /* ---- TRANSFER panel ---- */
  if(R.transfer){
    $('panel-transfer').style.display='';
    const TR=R.transfer, L=TR.laws;
    const markets=Object.keys(TR.sources);           // US first, then foreign
    const clsColor={TRANSFERS:'pos','UNIVERSE-SPECIFIC':'verdict-mixed'};
    let h='<tr><th>Market law</th>'+markets.map(m=>`<th>${m.toUpperCase()}</th>`).join('')+'<th>verdict</th></tr>';
    for(const [q,r] of Object.entries(L)){
      h+=`<tr><td>${q}</td>`+
        markets.map(m=>`<td>${r.values[m]!=null?r.values[m]:'—'}</td>`).join('')+
        `<td><span class="${clsColor[r.class]||''}">${r.class}</span></td></tr>`;}
    $('tbl-transfer-laws').innerHTML=h;
    const trans=Object.entries(L).filter(([q,r])=>r.class==='TRANSFERS').map(([q])=>q);
    $('sub-transfer-laws').innerHTML=`<b style="color:var(--green)">Transfer exactly (${TR.n_transfer}/${TR.n_laws}):</b> `+
      trans.join(', ')+`. The one-clock collapse itself holds everywhere (deformed kurtosis 3.3–3.8 in all four markets, vs raw 8–13); what varies is point values of H, commonality and the deformed branching ratio — mechanism universal, calibration local.`;

    let hf='<tr><th>Market</th><th>KRONOS Sharpe</th><th>index Sharpe</th><th>KRONOS MaxDD</th><th>index MaxDD</th></tr>';
    for(const m of markets){
      const f=TR.frozen[m]; if(!f) continue;
      const better=f.net.max_dd>=f.index.max_dd;      // shallower (less negative)
      hf+=`<tr><td${m==='US'?'':' style="color:var(--cyan)"'}>${m.toUpperCase()}</td>`+
        `<td>${f.net.sharpe.toFixed(2)}</td><td>${f.index.sharpe.toFixed(2)}</td>`+
        `<td class="${better?'pos':''}">${(f.net.max_dd*100).toFixed(0)}%</td>`+
        `<td>${(f.index.max_dd*100).toFixed(0)}%</td></tr>`;}
    $('tbl-transfer-frozen').innerHTML=hf;
    const H=TR.hypotheses;
    $('sub-transfer-frozen').innerHTML=`<b style="color:${H.TR2a&&H.TR2b?'var(--green)':'var(--amber)'}">`+
      `TR2 ${H.TR2a&&H.TR2b?'holds':'partial'}:</b> the US-tuned system, with every hyperparameter frozen, keeps a positive Sharpe AND a shallower drawdown than the local index in every foreign market. `+
      `<b style="color:var(--rose)">TR1 ${H.TR1?'holds':'fails'}</b> — only ${TR.n_transfer}/${TR.n_laws} laws transfer as exact values. The honest transferable claim is risk control, not alpha.`;
  }

  /* ---- CRYPTO panel ---- */
  if(R.crypto){
    $('panel-crypto').style.display='';
    const CR=R.crypto, L=CR.laws;
    const markets=[...CR.equity_markets,'crypto'];
    const clsColor={TRANSFERS:'pos','UNIVERSE-SPECIFIC':'verdict-mixed'};
    let h='<tr><th>law</th>'+markets.map(m=>`<th${m==='crypto'?' style="color:var(--amber)"':''}>${m==='asia_em'?'ASIA':m.toUpperCase()}</th>`).join('')+'<th>vs equities</th></tr>';
    for(const [q,r] of Object.entries(L)){
      const isLev=q==='leverage';
      h+=`<tr${isLev?' style="background:rgba(245,158,11,.10)"':''}><td>${q}</td>`+
        markets.map(m=>`<td${m==='crypto'?' style="color:var(--amber);font-weight:600"':''}>${r.values[m]!=null?r.values[m]:'—'}</td>`).join('')+
        `<td><span class="${clsColor[r.class]||''}">${r.class==='TRANSFERS'?'transfers':'differs'}</span></td></tr>`;}
    setHTML('tbl-crypto-laws',h);
    setHTML('sub-crypto-laws',`<b style="color:var(--green)">One-clock survives:</b> raw kurtosis ${L.kurt.values.crypto} collapses to ${L.kurt_def.values.crypto} after vol-deformation (equities ~3.5). Near-critical branching ${L.n_raw.values.crypto} matches equities and still collapses to ${L.n_def.values.crypto} — the reflexivity illusion (REFLEX) is asset-class-universal. Mechanism transfers; one law flips.`);

    const pc=CR.per_coin_leverage, lv=CR.leverage_contrast;
    const entries=Object.entries(pc).sort((a,b)=>a[1]-b[1]);
    const mx=Math.max(...entries.map(([,v])=>Math.abs(v)),0.05);
    let bars='<div style="font-size:11px">';
    for(const [coin,v] of entries){
      const w=Math.abs(v)/mx*48, pos=v>0;
      bars+=`<div style="display:flex;align-items:center;gap:8px;margin:3px 0">`+
        `<span style="width:48px;color:var(--faint);text-align:right">${coin.replace('-USD','')}</span>`+
        `<div style="flex:1;position:relative;height:12px;background:var(--panel2);border-radius:3px">`+
        `<div style="position:absolute;left:50%;top:0;width:1px;height:12px;background:var(--line)"></div>`+
        `<div style="position:absolute;${pos?'left:50%':'right:50%'};top:1px;height:10px;width:${w}%;background:${pos?'var(--green)':'var(--rose)'};border-radius:2px"></div>`+
        `</div><span style="width:50px;color:${pos?'var(--green)':'var(--rose)'}">${v>=0?'+':''}${v.toFixed(3)}</span></div>`;}
    const nInv=entries.filter(([,v])=>v>0).length;
    bars+=`</div><div class="sub" style="margin-top:6px"><b style="color:var(--green)">green = inverted (positive leverage)</b>, rose = equity-like. Crypto ${lv.crypto_leverage>=0?'+':''}${lv.crypto_leverage} vs equity cohort ${lv.equity_mean} (z=${lv.z_vs_equities}) — <b style="color:var(--amber)">${lv.verdict}, ${nInv}/${entries.length} coins flipped.</b></div>`;
    setHTML('ch-crypto-lev',bars);

    const HY=CR.hypotheses;
    const hyp=[['C1','One-clock collapse survives',HY.C1],['C2','Leverage weakens / inverts',HY.C2],['C3','More reflexive than equities',HY.C3],['C4','Fatter raw tails',HY.C4]];
    let ht='<tr><th>#</th><th>pre-registered prediction</th><th>verdict</th></tr>';
    for(const [id,desc,ok] of hyp)
      ht+=`<tr><td>${id}</td><td>${desc}</td><td><span class="${ok?'pos':'neg'}">${ok?'✓ holds':'✗ refuted'}</span></td></tr>`;
    setHTML('tbl-crypto-hyp',ht);
  }

  /* ---- synthesis ---- */
  new LineChart('ch-synth',[
    {name:'KRONOS-X',dates:syn.nav.dates,values:syn.nav.x,color:COL.cyan,width:2},
    {name:'KRONOS v1',dates:syn.nav.dates,values:syn.nav.v1,color:COL.violet,width:1.2,dash:[4,3]},
    {name:'Core (no overlay)',dates:syn.nav.dates,values:syn.nav.core,color:COL.green,width:1.2},
    {name:'SPY',dates:syn.nav.dates,values:syn.nav.spy,color:COL.dim,width:1.2},
  ],{height:280,fmt:fmt.nav,regimeBands:true});
  let hs2='<tr><th>Strategy</th><th>CAGR</th><th>Sharpe</th><th>MaxDD</th><th>CVaR95</th></tr>';
  for(const [nm,v] of Object.entries(syn.strategies))
    hs2+=`<tr><td>${nm}</td><td>${pct(v.cagr)}</td><td>${v.sharpe.toFixed(2)}</td>
      <td>${pct(v.max_dd)}</td><td>${(v.cvar95*100).toFixed(2)}%</td></tr>`;
  $('tbl-synth').innerHTML=hs2;
}

/* monthly heatmap */
(function(){
  const el=$('ch-mo'),M=DATA.monthly;
  const years=[...new Set(M.map(r=>r.y))].sort();
  const hh=years.length*20+50;
  const {c,ctx,tip}=setupCanvas(el,hh);
  const grid={}; M.forEach(r=>grid[r.y+'-'+r.m]=r.v);
  const yearTotals={}; years.forEach(y=>{let p=1;
    for(let m=1;m<=12;m++){const v=grid[y+'-'+m];if(v!=null)p*=1+v;}
    yearTotals[y]=p-1;});
  const MN=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const draw=()=>{
    const w=c.clientWidth;ctx.clearRect(0,0,w,hh);
    const x0=48,cw=(w-x0-78)/12,ch=20;
    ctx.font='10.5px ui-monospace,Menlo,monospace';
    ctx.textAlign='center';ctx.fillStyle='#5b6a84';
    MN.forEach((m,j)=>ctx.fillText(m,x0+j*cw+cw/2,14));
    ctx.fillText('YEAR',w-42,14);
    years.forEach((y,i)=>{
      ctx.fillStyle='#7d8ca3';ctx.textAlign='right';
      ctx.fillText(y,x0-7,24+i*ch+13);
      for(let m=1;m<=12;m++){
        const v=grid[y+'-'+m]; if(v==null)continue;
        ctx.fillStyle=divColor(v,0.06);
        ctx.fillRect(x0+(m-1)*cw,24+i*ch,cw-2,ch-3);
        ctx.fillStyle=Math.abs(v)>0.001?'#cfdcec':'#5b6a84';ctx.textAlign='center';
        ctx.fillText((v*100).toFixed(1),x0+(m-1)*cw+cw/2,24+i*ch+13);}
      const yt=yearTotals[y];
      ctx.fillStyle=yt>=0?COL.green:COL.rose;ctx.textAlign='right';
      ctx.fillText((yt*100).toFixed(1)+'%',w-12,24+i*ch+13);});
  };
  c._draw=draw;draw();
})();
</script>
</body>
</html>
"""
