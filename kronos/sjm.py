"""Statistical Jump Model for regime detection (KRONOS-X).

Fits regimes by penalized clustering (Bemporad & Boyd 2018; Nystrup et al.
applications): minimize sum of squared distances to state centers plus a
fixed penalty lambda per state switch. Solved by alternating between exact
dynamic-programming state assignment and center updates. No likelihood, no
Gaussian assumption, deterministic given the init — and the jump penalty
controls persistence *inside* the estimator instead of post-hoc hysteresis.

For the horse race the fitted model is wrapped with a statistical layer:
empirical transition matrix + per-state Gaussians, so it can emit the same
causal one-step-ahead predictive density as the HMMs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal


class JumpModel:
    def __init__(self, n_states: int = 3, lam: float = 16.0,
                 max_iter: int = 30, seed: int = 42):
        self.K = n_states
        self.lam = lam
        self.max_iter = max_iter
        self.seed = seed
        self.centers_ = None      # (K, D) in standardized space
        self.mu_ = None           # feature standardization
        self.sd_ = None
        self.states_ = None       # in-sample optimal path
        self.A_ = None            # empirical transition matrix
        self.means_ = None        # per-state Gaussian on RAW features
        self.covs_ = None
        self.objective_ = np.inf

    # ------------------------------------------------------------------ core
    def _standardize(self, X: np.ndarray, fit: bool) -> np.ndarray:
        if fit:
            self.mu_ = X.mean(axis=0)
            self.sd_ = X.std(axis=0) + 1e-12
        return (X - self.mu_) / self.sd_

    def _dp_assign(self, D: np.ndarray) -> np.ndarray:
        """Exact optimal state path for switch cost lam. D = (T,K) sq dists."""
        T, K = D.shape
        cost = D[0].copy()
        # choice[t,k]: -1 = stayed in k, else the state we switched from
        choice = np.full((T, K), -1, dtype=np.int32)
        lam = self.lam
        for t in range(1, T):
            a1 = int(cost.argmin())
            m1 = cost[a1]
            tmp = cost.copy(); tmp[a1] = np.inf
            a2 = int(tmp.argmin()); m2 = tmp[a2]
            switch_cost = np.full(K, m1 + lam)
            switch_from = np.full(K, a1, dtype=np.int32)
            switch_cost[a1] = m2 + lam
            switch_from[a1] = a2
            take_switch = switch_cost < cost
            choice[t] = np.where(take_switch, switch_from, -1)
            cost = D[t] + np.where(take_switch, switch_cost, cost)
        # backtrack
        states = np.empty(T, dtype=np.int32)
        states[-1] = int(cost.argmin())
        for t in range(T - 1, 0, -1):
            prev = choice[t, states[t]]
            states[t - 1] = states[t] if prev == -1 else prev
        self._final_cost = float(cost.min())
        return states

    def _sq_dists(self, Z: np.ndarray) -> np.ndarray:
        return ((Z[:, None, :] - self.centers_[None, :, :]) ** 2).sum(axis=2)

    def fit(self, X: np.ndarray) -> "JumpModel":
        Z = self._standardize(X, fit=True)
        rng = np.random.default_rng(self.seed)
        T, Dm = Z.shape
        best = None
        # deterministic vol-quantile init + 2 jittered restarts
        vol_order = np.argsort(Z[:, -1])
        for restart in range(3):
            buckets = np.array_split(vol_order, self.K)
            centers = np.array([Z[b].mean(axis=0) for b in buckets])
            if restart > 0:
                centers = centers + rng.normal(0, 0.3, centers.shape)
            self.centers_ = centers
            prev_states = None
            for _ in range(self.max_iter):
                states = self._dp_assign(self._sq_dists(Z))
                for k in range(self.K):
                    m = states == k
                    if m.sum() < 2:   # empty state: reseed at worst-fit point
                        far = self._sq_dists(Z).min(axis=1).argmax()
                        self.centers_[k] = Z[far]
                    else:
                        self.centers_[k] = Z[m].mean(axis=0)
                if prev_states is not None and np.array_equal(states, prev_states):
                    break
                prev_states = states
            obj = self._final_cost
            if best is None or obj < best[0]:
                best = (obj, self.centers_.copy(), states.copy())
        self.objective_, self.centers_, self.states_ = best
        self._fit_statistical_layer(X)
        self._canonicalize()
        return self

    # -------------------------------------------------- statistical wrapper
    def _fit_statistical_layer(self, X: np.ndarray) -> None:
        K, Dm = self.K, X.shape[1]
        s = self.states_
        # transition matrix with Dirichlet pseudocount
        A = np.ones((K, K))
        for a, b in zip(s[:-1], s[1:]):
            A[a, b] += 1
        self.A_ = A / A.sum(axis=1, keepdims=True)
        self.means_ = np.zeros((K, Dm))
        self.covs_ = np.zeros((K, Dm, Dm))
        gcov = np.cov(X.T) + np.eye(Dm) * 1e-10
        for k in range(K):
            m = s == k
            if m.sum() < 2 * Dm:
                self.means_[k] = X.mean(axis=0)
                self.covs_[k] = gcov
            else:
                self.means_[k] = X[m].mean(axis=0)
                self.covs_[k] = np.cov(X[m].T) + np.eye(Dm) * 1e-10

    def _canonicalize(self) -> None:
        """0=Bull, 1=Volatile, 2=Bear — same convention as the HMM."""
        mean_ret = self.means_[:, 0]
        vol = np.sqrt(self.covs_[:, 0, 0])
        bear = int(np.argmin(mean_ret))
        rest = [k for k in range(self.K) if k != bear]
        bull = rest[int(np.argmin(vol[rest]))] if len(rest) > 1 else rest[0]
        middle = [k for k in range(self.K) if k not in (bear, bull)]
        order = [bull] + middle + [bear]
        inv = np.empty(self.K, dtype=np.int32)
        for new, old in enumerate(order):
            inv[old] = new
        self.centers_ = self.centers_[order]
        self.means_ = self.means_[order]
        self.covs_ = self.covs_[order]
        self.A_ = self.A_[np.ix_(order, order)]
        self.states_ = inv[self.states_]

    def online_states(self, X: np.ndarray) -> np.ndarray:
        """Causal state estimate: terminal argmin of the DP forward pass at
        each prefix length — uses only data <= t, no backtracking."""
        Z = (X - self.mu_) / self.sd_
        D = self._sq_dists(Z)
        T, K = D.shape
        cost = D[0].copy()
        out = np.empty(T, dtype=np.int32)
        out[0] = int(cost.argmin())
        lam = self.lam
        for t in range(1, T):
            a1 = int(cost.argmin()); m1 = cost[a1]
            tmp = cost.copy(); tmp[a1] = np.inf
            m2 = tmp.min()
            switch_cost = np.full(K, m1 + lam)
            switch_cost[a1] = m2 + lam
            cost = D[t] + np.minimum(cost, switch_cost)
            out[t] = int(cost.argmin())
        return out

    def predictive_logpdf_return(self, state_now: int, r_next: float) -> float:
        """log p(r_{t+1} | s_t): mixture over next state via A, marginal on
        the return dimension (dim 0) of the per-state Gaussians."""
        p = 0.0
        for k in range(self.K):
            w = self.A_[state_now, k]
            sd = np.sqrt(self.covs_[k][0, 0])
            p += w * np.exp(-0.5 * ((r_next - self.means_[k][0]) / sd) ** 2) \
                 / (sd * np.sqrt(2 * np.pi))
        return float(np.log(max(p, 1e-300)))
