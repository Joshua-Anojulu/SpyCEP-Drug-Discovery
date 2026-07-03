from spycep_drug_discovery.statistics_analysis import (
    bootstrap_mean_difference,
    mann_whitney,
    positive_control_margin,
)


def test_bootstrap_ci_excludes_zero_for_separated_groups():
    a = [10.0, 11.0, 9.5, 10.5, 10.2]
    b = [1.0, 2.0, 1.5, 0.5, 1.2]

    result = bootstrap_mean_difference(a, b, n_resamples=2000, seed=42)

    assert result["observed_difference"] > 0
    assert result["excludes_zero"] is True


def test_bootstrap_ci_includes_zero_for_overlapping_groups():
    a = [5.0, 5.1, 4.9, 5.2, 4.8]
    b = [5.05, 4.95, 5.1, 4.9, 5.0]

    result = bootstrap_mean_difference(a, b, n_resamples=2000, seed=42)

    assert result["excludes_zero"] is False


def test_mann_whitney_small_p_for_separated_groups():
    result = mann_whitney([10, 11, 12, 13], [1, 2, 3, 4])

    assert result["p_value"] < 0.05


def test_positive_control_margin():
    result = positive_control_margin(-6.75, [-5.55, -5.27, -5.22, -4.75, -5.07, -4.40, -4.72])

    assert result["beats_all_decoys"] is True
    assert result["best_decoy_affinity"] == -5.55
    assert abs(result["margin_to_best_decoy"] - 1.20) < 1e-6
    assert result["sd_stronger_than_decoy_mean"] > 0
