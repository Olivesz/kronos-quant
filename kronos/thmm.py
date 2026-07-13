"""Student-t Hidden Markov Model (KRONOS-X², Study 1).

The control experiment for "regimes vs fat tails": each state emits a
multivariate Student-t, so leptokurtosis is modeled *within* states and
extra states are no longer rewarded for faking it.

Fit by ECM. E-step: state responsibilities gamma from forward-backward
(t emissions) plus the classic latent-scale weights
    u_tk = (nu_k + d) / (nu_k + delta_tk),   delta = Mahalanobis^2.
CM-steps: gamma*u-weighted mean; scatter = sum(gamma*u*xx')/sum(gamma)
(Kent-Tyler-Vardi normalization — exact ML form for t scatter);
nu_k solves the standard digamma equation
    log(nu/2) - psi(nu/2) + 1 + c_k + psi((nu+d)/2) - log((nu+d)/2) = 0,
    c_k = sum_t gamma (log u - u) / sum_t gamma   (<= -1 always),
by Brent's method on [2.05, 300]; the bracket endpoints are the
"infinite-variance" and "effectively Gaussian" clamps.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import brentq
from scipy.special import digamma, gammaln

from kronos.regime import GaussianHMM


def _mvt_logpdf(X: np.ndarray, mu: np.ndarray, cov: np.ndarray,
                nu: float) -> tuple[np.ndarray, np.ndarray]:
    """Returns (logpdf, mahalanobis^2) for all rows of X."""
    d = X.shape[1]
    cf = cho_factor(cov + np.eye(d) * 1e-12, lower=True)
    diff = X - mu
    sol = cho_solve(cf, diff.T)            # (d, T)
    delta = np.einsum("td,dt->t", diff, sol)
    logdet = 2.0 * np.log(np.diag(cf[0])).sum()
    lp = (gammaln((nu + d) / 2) - gammaln(nu / 2)
          - 0.5 * d * np.log(nu * np.pi) - 0.5 * logdet
          - 0.5 * (nu + d) * np.log1p(delta / nu))
    return lp, delta


def _solve_nu(c_k: float, d: int, lo: float = 2.05, hi: float = 300.0) -> float:
    """Root of the ECM nu equation; c_k <= -1 guarantees f(hi) <= 0."""
    def f(nu):
        return (np.log(nu / 2) - digamma(nu / 2) + 1.0 + c_k
                + digamma((nu + d) / 2) - np.log((nu + d) / 2))
    f_lo, f_hi = f(lo), f(hi)
    if f_lo <= 0:        # even nu=2.05 too thin-tailed for the data: clamp
        return lo
    if f_hi >= 0:        # effectively Gaussian
        return hi
    return float(brentq(f, lo, hi, xtol=1e-3))


class StudentTHMM(GaussianHMM):
    def __init__(self, n_states: int = 3, max_iter: int = 200,
                 tol: float = 1e-6, seed: int = 42):
        super().__init__(n_states, max_iter, tol, seed)
        self.nus_ = None     # (K,) per-state degrees of freedom

    # ------------------------------------------------------------- emissions
    def _log_obs(self, X: np.ndarray) -> np.ndarray:
        T = len(X)
        logB = np.empty((T, self.K))
        self._delta_cache = np.empty((T, self.K))
        for k in range(self.K):
            lp, delta = _mvt_logpdf(X, self.means_[k], self.covs_[k],
                                    self.nus_[k])
            logB[:, k] = lp
            self._delta_cache[:, k] = delta
        return logB

    def _init_params(self, X, jitter=0.0, rng=None):
        super()._init_params(X, jitter, rng)
        self.nus_ = np.full(self.K, 8.0)

    # ------------------------------------------------------------------ ECM
    def _em(self, X: np.ndarray) -> float:
        from scipy.special import logsumexp
        T, D = X.shape
        prev_ll = -np.inf
        for _ in range(self.max_iter):
            logB = self._log_obs(X)               # also fills delta cache
            delta = self._delta_cache
            log_alpha = self._forward(logB)
            log_beta = self._backward(logB)
            ll = logsumexp(log_alpha[-1])

            log_gamma = log_alpha + log_beta
            log_gamma -= logsumexp(log_gamma, axis=1, keepdims=True)
            gamma = np.exp(log_gamma)

            logA = np.log(self.A_ + 1e-300)
            log_xi = (log_alpha[:-1, :, None] + logA[None, :, :]
                      + logB[1:, None, :] + log_beta[1:, None, :])
            log_xi -= logsumexp(log_xi, axis=(1, 2), keepdims=True)
            xi = np.exp(log_xi)

            self.pi_ = (gamma[0] + 1e-6) / (gamma[0] + 1e-6).sum()
            num = xi.sum(axis=0) + 1.0
            self.A_ = num / num.sum(axis=1, keepdims=True)

            for k in range(self.K):
                g = gamma[:, k]
                Nk = g.sum()
                if Nk < 2 * D:                    # collapsed state: reseed
                    qs = np.quantile(X, 0.1 + 0.4 * k / max(self.K - 1, 1),
                                     axis=0)
                    self.means_[k] = qs
                    self.covs_[k] = np.cov(X.T) + np.eye(D) * 1e-6
                    self.nus_[k] = 8.0
                    continue
                nu = self.nus_[k]
                u = (nu + D) / (nu + delta[:, k])
                gu = g * u
                mu = gu @ X / gu.sum()
                Xc = X - mu
                cov = (Xc * gu[:, None]).T @ Xc / Nk    # KTV normalization
                cov += np.eye(D) * 1e-10
                dg = np.maximum(np.diag(cov), 1e-10)
                cov[np.diag_indices(D)] = dg
                c_k = float((g * (np.log(u) - u)).sum() / Nk)
                self.means_[k] = mu
                self.covs_[k] = cov
                self.nus_[k] = _solve_nu(c_k, D)

            if abs(ll - prev_ll) < self.tol * max(abs(prev_ll), 1.0):
                prev_ll = ll
                break
            prev_ll = ll
        return prev_ll

    # ---------------------------------------------------------------- admin
    def fit(self, X: np.ndarray, n_restarts: int = 3,
            init_from: "StudentTHMM | None" = None) -> "StudentTHMM":
        if init_from is not None and init_from.means_ is not None:
            self.means_ = init_from.means_.copy()
            self.covs_ = init_from.covs_.copy()
            self.A_ = init_from.A_.copy()
            self.pi_ = init_from.pi_.copy()
            self.nus_ = init_from.nus_.copy()
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
                        self.A_.copy(), self.pi_.copy(), self.nus_.copy())
        (self.loglik_, self.means_, self.covs_,
         self.A_, self.pi_, self.nus_) = best
        self._canonicalize()
        return self

    def _canonicalize(self) -> None:
        """Order by ACTUAL variance (scale * nu/(nu-2)), not raw scale —
        a low-scale/low-nu state can be riskier than it looks."""
        mean_ret = self.means_[:, 0]
        nu_fac = np.where(self.nus_ > 2.2, self.nus_ / (self.nus_ - 2), 10.0)
        var0 = np.array([self.covs_[k][0, 0] for k in range(self.K)]) * nu_fac
        bear = int(np.argmin(mean_ret))
        rest = [k for k in range(self.K) if k != bear]
        bull = rest[int(np.argmin(var0[rest]))] if len(rest) > 1 else rest[0]
        middle = sorted((k for k in range(self.K) if k not in (bear, bull)),
                        key=lambda k: var0[k])
        order = [bull] + middle + [bear]
        self.means_ = self.means_[order]
        self.covs_ = self.covs_[order]
        self.pi_ = self.pi_[order]
        self.nus_ = self.nus_[order]
        self.A_ = self.A_[np.ix_(order, order)]

    def return_marginal_logdens(self, pred_w: np.ndarray,
                                r: np.ndarray) -> np.ndarray:
        """log p(r) under the mixture, marginal of dim 0 (univariate t)."""
        dens = np.zeros(len(r))
        for k in range(self.K):
            nu = self.nus_[k]
            s = np.sqrt(self.covs_[k][0, 0])
            z = (r - self.means_[k][0]) / s
            lp = (gammaln((nu + 1) / 2) - gammaln(nu / 2)
                  - 0.5 * np.log(nu * np.pi) - np.log(s)
                  - 0.5 * (nu + 1) * np.log1p(z * z / nu))
            dens += pred_w[:, k] * np.exp(lp)
        return np.log(np.maximum(dens, 1e-300))
