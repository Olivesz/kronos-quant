"""Duration HMM (semi-Markov) via the expanded-state construction (KRONOS-X).

Each of K regimes is expanded into r tied sub-states arranged left-to-right
with self-loops:  (k,0) -> (k,1) -> ... -> (k,r-1) -> exit to (j,0).
Regime duration is then a sum of r geometrics — negative-binomial — which is
humped like real bull/bear spell lengths, unlike the HMM's memoryless
geometric. Emissions are hard-tied across sub-states of a regime, so the
model has the same emission complexity as the plain HMM; only the duration
law gains flexibility. EM preserves the structural zeros of the transition
mask automatically.
"""
from __future__ import annotations

import numpy as np
from scipy.special import logsumexp

from kronos.regime import GaussianHMM


class DurationHMM(GaussianHMM):
    def __init__(self, n_regimes: int = 3, r: int = 3, max_iter: int = 200,
                 tol: float = 1e-6, seed: int = 42):
        super().__init__(n_states=n_regimes * r, max_iter=max_iter,
                         tol=tol, seed=seed)
        self.Kreg = n_regimes
        self.r = r
        self.mask_ = self._build_mask()

    # ----------------------------------------------------------- structure
    def _sub(self, k: int, i: int) -> int:
        return k * self.r + i

    def _build_mask(self) -> np.ndarray:
        K, r = self.Kreg, self.r
        M = np.zeros((K * r, K * r))
        for k in range(K):
            for i in range(r):
                s = self._sub(k, i)
                M[s, s] = 1.0                       # self-loop
                if i < r - 1:
                    M[s, self._sub(k, i + 1)] = 1.0  # advance
                else:
                    for j in range(K):              # exit to other regimes
                        if j != k:
                            M[s, self._sub(j, 0)] = 1.0
        return M

    def _init_params(self, X: np.ndarray, jitter: float = 0.0, rng=None) -> None:
        T, D = X.shape
        vol = X[:, -1]
        order = np.argsort(vol)
        buckets = np.array_split(order, self.Kreg)
        means, covs = [], []
        for idx in buckets:
            mu = X[idx].mean(axis=0)
            if jitter > 0 and rng is not None:
                mu = mu + rng.normal(0, jitter, D) * X.std(axis=0)
            cv = np.cov(X[idx].T) + np.eye(D) * 1e-8
            for _ in range(self.r):                  # replicate to sub-states
                means.append(mu.copy())
                covs.append(cv.copy())
        self.means_ = np.array(means)
        self.covs_ = np.array(covs)
        # masked initial transitions: heavy self-loop, rest spread on mask
        A = self.mask_ * 0.05
        np.fill_diagonal(A, 0.93)
        A = A * self.mask_
        self.A_ = A / A.sum(axis=1, keepdims=True)
        self.pi_ = np.full(self.K, 1.0 / self.K)

    # ------------------------------------------------------------------ EM
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
            gamma = np.exp(log_gamma)

            with np.errstate(divide="ignore"):
                logA = np.where(self.A_ > 0, np.log(self.A_ + 1e-300), -np.inf)
            log_xi = (log_alpha[:-1, :, None] + logA[None, :, :]
                      + logB[1:, None, :] + log_beta[1:, None, :])
            log_xi -= logsumexp(log_xi, axis=(1, 2), keepdims=True)
            xi = np.exp(log_xi)

            self.pi_ = (gamma[0] + 1e-6) / (gamma[0] + 1e-6).sum()
            num = xi.sum(axis=0) + 0.5 * self.mask_   # pseudocount on mask only
            num = num * self.mask_                    # enforce structure
            rowsum = num.sum(axis=1, keepdims=True)
            self.A_ = np.where(rowsum > 0, num / rowsum, self.mask_ /
                               self.mask_.sum(axis=1, keepdims=True))

            # tied emission M-step: pool gammas across each regime's sub-states
            for k in range(self.Kreg):
                cols = [self._sub(k, i) for i in range(self.r)]
                g = gamma[:, cols].sum(axis=1)
                Nk = g.sum()
                if Nk < 2 * D:
                    qs = np.quantile(X, 0.1 + 0.4 * k / max(self.Kreg - 1, 1), axis=0)
                    mu, cov = qs, np.cov(X.T) + np.eye(D) * 1e-6
                else:
                    w = g / Nk
                    mu = w @ X
                    Xc = X - mu
                    cov = (Xc * w[:, None]).T @ Xc + np.eye(D) * 1e-10
                    d = np.maximum(np.diag(cov), 1e-10)
                    cov[np.diag_indices(D)] = d
                for c in cols:
                    self.means_[c] = mu
                    self.covs_[c] = cov

            if abs(ll - prev_ll) < self.tol * max(abs(prev_ll), 1.0):
                prev_ll = ll
                break
            prev_ll = ll
        return prev_ll

    # ----------------------------------------------------- regime-level API
    def _canonicalize(self) -> None:
        mean_ret = np.array([self.means_[self._sub(k, 0)][0] for k in range(self.Kreg)])
        vol = np.array([np.sqrt(self.covs_[self._sub(k, 0)][0, 0]) for k in range(self.Kreg)])
        bear = int(np.argmin(mean_ret))
        rest = [k for k in range(self.Kreg) if k != bear]
        bull = rest[int(np.argmin(vol[rest]))] if len(rest) > 1 else rest[0]
        middle = [k for k in range(self.Kreg) if k not in (bear, bull)]
        order = [bull] + middle + [bear]
        perm = []
        for new_k in range(self.Kreg):
            old_k = order[new_k]
            perm += [self._sub(old_k, i) for i in range(self.r)]
        perm = np.array(perm)
        self.means_ = self.means_[perm]
        self.covs_ = self.covs_[perm]
        self.pi_ = self.pi_[perm]
        self.A_ = self.A_[np.ix_(perm, perm)]
        # mask is order-invariant by construction (same block structure)

    def regime_probs(self, sub_probs: np.ndarray) -> np.ndarray:
        """(T, K*r) sub-state probabilities -> (T, Kreg) regime probabilities."""
        T = sub_probs.shape[0]
        out = np.zeros((T, self.Kreg))
        for k in range(self.Kreg):
            cols = [self._sub(k, i) for i in range(self.r)]
            out[:, k] = sub_probs[:, cols].sum(axis=1)
        return out

    def duration_pmf(self, k: int, dmax: int = 250) -> np.ndarray:
        """Implied regime-duration distribution (for the dashboard).
        Computed by absorbing-chain simulation over the sub-state block."""
        r = self.r
        block = self.A_[np.ix_([self._sub(k, i) for i in range(r)],
                               [self._sub(k, i) for i in range(r)])]
        p = np.zeros(r); p[0] = 1.0
        pmf = np.zeros(dmax)
        for d in range(dmax):
            stay = p @ block
            pmf[d] = p.sum() - stay.sum()   # prob of exiting on day d+1
            p = stay
        return pmf
