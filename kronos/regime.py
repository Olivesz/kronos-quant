"""Gaussian Hidden Markov Model regime detection, implemented from scratch.

Log-space Baum-Welch EM, deterministic quantile initialization, canonical
state labeling (Bull / Volatile / Bear), and a strict walk-forward driver
that only ever exposes *filtered* probabilities (data through t) to trading.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import logsumexp
from scipy.stats import multivariate_normal


class GaussianHMM:
    def __init__(self, n_states: int = 3, max_iter: int = 200, tol: float = 1e-6,
                 seed: int = 42):
        self.K = n_states
        self.max_iter = max_iter
        self.tol = tol
        self.seed = seed
        self.means_ = None      # (K, D)
        self.covs_ = None       # (K, D, D)
        self.A_ = None          # (K, K) transition matrix
        self.pi_ = None         # (K,) initial distribution
        self.loglik_ = -np.inf

    # ------------------------------------------------------------------ utils
    def _log_obs(self, X: np.ndarray) -> np.ndarray:
        """(T, K) log emission probabilities."""
        T = len(X)
        logB = np.empty((T, self.K))
        for k in range(self.K):
            logB[:, k] = multivariate_normal.logpdf(
                X, mean=self.means_[k], cov=self.covs_[k], allow_singular=True)
        return logB

    def _init_params(self, X: np.ndarray, jitter: float = 0.0,
                     rng: np.random.Generator | None = None) -> None:
        """Deterministic init: bucket days by realized-vol feature terciles."""
        T, D = X.shape
        vol_feature = X[:, -1]  # last feature is log realized vol
        order = np.argsort(vol_feature)
        buckets = np.array_split(order, self.K)
        means, covs = [], []
        for idx in buckets:
            mu = X[idx].mean(axis=0)
            if jitter > 0 and rng is not None:
                mu = mu + rng.normal(0, jitter, D) * X.std(axis=0)
            cv = np.cov(X[idx].T) + np.eye(D) * 1e-8
            means.append(mu)
            covs.append(cv)
        self.means_ = np.array(means)
        self.covs_ = np.array(covs)
        self.A_ = np.full((self.K, self.K), 0.05 / (self.K - 1))
        np.fill_diagonal(self.A_, 0.95)
        self.pi_ = np.full(self.K, 1.0 / self.K)

    # ------------------------------------------------------------- inference
    # Scaled forward/backward: re-center by the running max each step, then a
    # single matmul replaces per-step logsumexp. Numerically equivalent.
    def _forward(self, logB: np.ndarray):
        T = len(logB)
        A = self.A_
        log_alpha = np.empty((T, self.K))
        log_alpha[0] = np.log(self.pi_) + logB[0]
        for t in range(1, T):
            prev = log_alpha[t - 1]
            m = prev.max()
            log_alpha[t] = logB[t] + m + np.log(np.exp(prev - m) @ A + 1e-300)
        return log_alpha

    def _backward(self, logB: np.ndarray):
        T = len(logB)
        A = self.A_
        log_beta = np.zeros((T, self.K))
        for t in range(T - 2, -1, -1):
            nxt = logB[t + 1] + log_beta[t + 1]
            m = nxt.max()
            log_beta[t] = m + np.log(A @ np.exp(nxt - m) + 1e-300)
        return log_beta

    def fit(self, X: np.ndarray, n_restarts: int = 3,
            init_from: "GaussianHMM | None" = None) -> "GaussianHMM":
        """Full fit with restarts, or a fast warm-started refit."""
        if init_from is not None and init_from.means_ is not None:
            self.means_ = init_from.means_.copy()
            self.covs_ = init_from.covs_.copy()
            self.A_ = init_from.A_.copy()
            self.pi_ = init_from.pi_.copy()
            self.loglik_ = self._em(X)
            self._canonicalize()
            return self
        rng = np.random.default_rng(self.seed)
        best = None
        for r in range(n_restarts):
            self._init_params(X, jitter=0.0 if r == 0 else 0.15, rng=rng)
            ll = self._em(X)
            if best is None or ll > best[0]:
                best = (ll, self.means_.copy(), self.covs_.copy(),
                        self.A_.copy(), self.pi_.copy())
        self.loglik_, self.means_, self.covs_, self.A_, self.pi_ = best
        self._canonicalize()
        return self

    def _em(self, X: np.ndarray) -> float:
        T, D = X.shape
        prev_ll = -np.inf
        for _ in range(self.max_iter):
            logB = self._log_obs(X)
            log_alpha = self._forward(logB)
            log_beta = self._backward(logB)
            ll = logsumexp(log_alpha[-1])

            log_gamma = log_alpha + log_beta
            log_gamma -= logsumexp(log_gamma, axis=1, keepdims=True)
            gamma = np.exp(log_gamma)  # (T, K)

            # xi: (T-1, K, K)
            logA = np.log(self.A_)
            log_xi = (log_alpha[:-1, :, None] + logA[None, :, :]
                      + logB[1:, None, :] + log_beta[1:, None, :])
            log_xi -= logsumexp(log_xi, axis=(1, 2), keepdims=True)
            xi = np.exp(log_xi)

            # M-step with pseudocounts for stability
            self.pi_ = (gamma[0] + 1e-6) / (gamma[0] + 1e-6).sum()
            num = xi.sum(axis=0) + 1.0  # Dirichlet pseudocount
            self.A_ = num / num.sum(axis=1, keepdims=True)

            Nk = gamma.sum(axis=0)  # (K,)
            for k in range(self.K):
                if Nk[k] < 2 * D:   # collapsed state -> re-seed from tails
                    qs = np.quantile(X, [0.1 + 0.4 * k / max(self.K - 1, 1)], axis=0)
                    self.means_[k] = qs[0]
                    self.covs_[k] = np.cov(X.T) + np.eye(D) * 1e-6
                    continue
                w = gamma[:, k] / Nk[k]
                mu = w @ X
                Xc = X - mu
                cov = (Xc * w[:, None]).T @ Xc
                cov += np.eye(D) * 1e-10
                # variance floor on the diagonal
                d = np.diag(cov).copy()
                d[d < 1e-10] = 1e-10
                cov[np.diag_indices(D)] = d
                self.means_[k] = mu
                self.covs_[k] = cov

            if abs(ll - prev_ll) < self.tol * max(abs(prev_ll), 1.0):
                prev_ll = ll
                break
            prev_ll = ll
        return prev_ll

    def _canonicalize(self) -> None:
        """Stable labels: 0=Bull (calmest non-bear), last=Bear (worst mean),
        middle states ordered by volatility. Works for any K >= 2."""
        mean_ret = self.means_[:, 0]
        vol = np.sqrt(np.array([self.covs_[k][0, 0] for k in range(self.K)]))
        bear = int(np.argmin(mean_ret))
        rest = [k for k in range(self.K) if k != bear]
        bull = rest[int(np.argmin(vol[rest]))] if len(rest) > 1 else rest[0]
        middle = sorted((k for k in range(self.K) if k not in (bear, bull)),
                        key=lambda k: vol[k])
        order = [bull] + middle + [bear]
        self.means_ = self.means_[order]
        self.covs_ = self.covs_[order]
        self.pi_ = self.pi_[order]
        self.A_ = self.A_[np.ix_(order, order)]

    def filtered_probs(self, X: np.ndarray) -> np.ndarray:
        """P(s_t | x_{1:t}) — causal, safe for trading."""
        logB = self._log_obs(X)
        log_alpha = self._forward(logB)
        log_f = log_alpha - logsumexp(log_alpha, axis=1, keepdims=True)
        return np.exp(log_f)

    def return_marginal_logdens(self, pred_w: np.ndarray,
                                r: np.ndarray) -> np.ndarray:
        """log p(r) under the state mixture, Gaussian marginal of dim 0."""
        mu = self.means_[:, 0]
        sd = np.sqrt(self.covs_[:, 0, 0])
        dens = (pred_w * np.exp(-0.5 * ((r[:, None] - mu) / sd) ** 2)
                / (sd * np.sqrt(2 * np.pi))).sum(axis=1)
        return np.log(np.maximum(dens, 1e-300))

    def smoothed_probs(self, X: np.ndarray) -> np.ndarray:
        """P(s_t | x_{1:T}) — uses the future; charts only, never trading."""
        logB = self._log_obs(X)
        la, lb = self._forward(logB), self._backward(logB)
        lg = la + lb
        lg -= logsumexp(lg, axis=1, keepdims=True)
        return np.exp(lg)


# ---------------------------------------------------------------------------
# Walk-forward driver
# ---------------------------------------------------------------------------

def build_features(market_rets: pd.Series, vol_window: int) -> pd.DataFrame:
    rv = market_rets.rolling(vol_window).std() * np.sqrt(252)
    feats = pd.DataFrame({
        "ret": market_rets,
        "logvol": np.log(rv.clip(lower=1e-4)),
    }).dropna()
    return feats


def walkforward_regimes(market_rets: pd.Series, cfg) -> dict:
    """Expanding-window walk-forward HMM.

    Returns dict with:
      filtered  : (T, K) DataFrame of causal probabilities
      smoothed  : (T, K) DataFrame (full final fit; charts only)
      regime    : Series of hysteresis-stabilized regime ids (causal)
      model     : final fitted GaussianHMM
    """
    feats = build_features(market_rets, cfg.hmm_vol_window)
    X = feats.to_numpy()
    idx = feats.index
    T = len(X)
    K = cfg.n_states

    filtered = np.full((T, K), np.nan)
    model = None
    refits = 0
    t = cfg.hmm_min_train
    while t < T:
        m = GaussianHMM(K, cfg.hmm_max_iter if model is None else 25,
                        cfg.hmm_tol, cfg.seed)
        model = m.fit(X[:t], init_from=model)
        refits += 1
        t_next = min(t + cfg.hmm_refit_every, T)
        # filtered probs are causal: prob at time s uses data x_{1:s} only
        fp = model.filtered_probs(X[:t_next])
        filtered[t - 1:t_next] = fp[t - 1:t_next]
        t = t_next

    filtered_df = pd.DataFrame(filtered, index=idx, columns=["Bull", "Volatile", "Bear"])

    # hysteresis: flip only after a confirmation streak, and respect a minimum
    # dwell time unless the new state is near-certain (a real crash overrides)
    regime = np.full(T, -1)
    current = -1
    streak_state, streak = -1, 0
    dwell = 0
    filled = np.where(np.isnan(filtered), -1.0, filtered)
    argmax = filled.argmax(axis=1)
    maxp = filled.max(axis=1)
    for i in range(T):
        if np.isnan(filtered[i]).any():
            continue
        cand = argmax[i]
        if current == -1:
            current = cand
        dwell += 1
        if cand != current and maxp[i] >= cfg.hmm_hysteresis_prob:
            if cand == streak_state:
                streak += 1
            else:
                streak_state, streak = cand, 1
            confirmed = streak >= cfg.hmm_hysteresis_days
            urgent = maxp[i] >= cfg.hmm_urgent_prob
            if confirmed and (dwell >= cfg.hmm_min_dwell or urgent):
                current = cand
                streak_state, streak = -1, 0
                dwell = 0
        else:
            streak_state, streak = -1, 0
        regime[i] = current

    regime_s = pd.Series(regime, index=idx, name="regime")
    smoothed = pd.DataFrame(model.smoothed_probs(X), index=idx,
                            columns=["Bull", "Volatile", "Bear"])
    return {"filtered": filtered_df, "smoothed": smoothed,
            "regime": regime_s, "model": model, "refits": refits}
