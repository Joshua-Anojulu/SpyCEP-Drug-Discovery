from spycep_drug_discovery.feasibility import score_structure
from spycep_drug_discovery.rcsb import RcsbEntryMetadata


def test_score_structure_rates_high_resolution_xray_as_strong_starting_point():
    metadata = RcsbEntryMetadata(
        pdb_id="7EDD",
        title="Crystal structure of a serine protease from Streptococcus pyogenes",
        method="X-RAY DIFFRACTION",
        resolution_angstrom=2.897,
    )

    score = score_structure(metadata)

    assert score.pdb_id == "7EDD"
    assert score.resolution_flag == "usable"
    assert score.method_flag == "experimental"
    assert score.overall_flag == "manual_review_required"
    assert "manual pocket review required" in score.notes


def test_score_structure_flags_missing_resolution_as_review_required():
    metadata = RcsbEntryMetadata(
        pdb_id="XXXX",
        title="Structure with missing resolution",
        method="X-RAY DIFFRACTION",
        resolution_angstrom=None,
    )

    score = score_structure(metadata)

    assert score.resolution_flag == "missing"
    assert score.overall_flag == "review_required"
