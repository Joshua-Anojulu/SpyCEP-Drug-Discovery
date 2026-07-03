from __future__ import annotations

from typing import Any, Sequence


def bootstrap_mean_difference(
    group_a: Sequence[float],
    group_b: Sequence[float],
    *,
    n_resamples: int = 10000,
    seed: int = 42,
) -> dict[str, Any]:
    """95% bootstrap CI for mean(group_a) - mean(group_b)."""
    import numpy as np

    rng = np.random.default_rng(seed)
    a = np.asarray(group_a, dtype=float)
    b = np.asarray(group_b, dtype=float)
    observed = float(a.mean() - b.mean())
    diffs = np.empty(n_resamples)
    for i in range(n_resamples):
        diffs[i] = rng.choice(a, a.size, replace=True).mean() - rng.choice(b, b.size, replace=True).mean()
    low, high = np.percentile(diffs, [2.5, 97.5])
    return {
        "observed_difference": observed,
        "ci95_low": float(low),
        "ci95_high": float(high),
        "n_resamples": n_resamples,
        "excludes_zero": bool(low > 0 or high < 0),
    }


def mann_whitney(group_a: Sequence[float], group_b: Sequence[float]) -> dict[str, Any]:
    from scipy import stats

    result = stats.mannwhitneyu(group_a, group_b, alternative="two-sided")
    return {"u_statistic": float(result.statistic), "p_value": float(result.pvalue)}


def positive_control_margin(positive: float, decoys: Sequence[float]) -> dict[str, Any]:
    """Summarize how far a positive control (more negative = stronger) beats its decoys."""
    import numpy as np

    d = np.asarray(decoys, dtype=float)
    decoy_sd = float(d.std(ddof=1))
    return {
        "positive_affinity": float(positive),
        "best_decoy_affinity": float(d.min()),
        "margin_to_best_decoy": float(d.min() - positive),
        "decoy_mean": float(d.mean()),
        "decoy_sd": decoy_sd,
        "sd_stronger_than_decoy_mean": float((d.mean() - positive) / decoy_sd) if decoy_sd else None,
        "beats_all_decoys": bool(positive < d.min()),
    }
