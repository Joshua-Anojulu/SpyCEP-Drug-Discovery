import json

from scripts.analyze_target_feasibility import _load_metadata_snapshot, _markdown_report, _rows_for_target
from spycep_drug_discovery.structure_review import load_structure_review_registry
from spycep_drug_discovery.targets import StructureCandidate, Target


def test_load_metadata_snapshot_reads_normalized_rcsb_metadata(tmp_path):
    snapshot_path = tmp_path / "rcsb_metadata.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "source": "RCSB Data API",
                "entries": [
                    {
                        "pdb_id": "7EDD",
                        "title": "Crystal structure of a serine protease from Streptococcus pyogenes",
                        "method": "X-RAY DIFFRACTION",
                        "resolution_angstrom": 2.897,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    metadata = _load_metadata_snapshot(snapshot_path)

    assert metadata["7EDD"].method == "X-RAY DIFFRACTION"
    assert metadata["7EDD"].resolution_angstrom == 2.897


def test_rows_for_target_reads_tracked_rcsb_metadata_and_structure_review(tmp_path):
    review_path = tmp_path / "docs" / "methods" / "structure_review.json"
    review_path.parent.mkdir(parents=True)
    review_path.write_text(
        json.dumps(
            {
                "review_version": "2026-07-01",
                "structures": [
                    {
                        "target_id": "spycep_scpC",
                        "pdb_id": "7EDD",
                        "chain_coverage": "pending manual review",
                        "missing_regions": "pending manual review",
                        "catalytic_region_status": "pending",
                        "pocket_definition_status": "pending",
                        "docking_readiness": "pending",
                        "review_notes": "Manual pocket/catalytic-site review has not been completed.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    target = Target(
        target_id="spycep_scpC",
        decision_role="primary",
        protein_name="Chemokine protease C / SpyCEP / ScpC",
        gene_name="scpC",
        organism="Streptococcus pyogenes",
        uniprot_accession="Q3HV58",
        rationale="Primary target",
        key_references=(),
        structures=(
            StructureCandidate(
                pdb_id="7EDD",
                source="RCSB",
                selection_note="Candidate SpyCEP/ScpC structure from UniProt cross-reference.",
            ),
        ),
    )
    reviews = load_structure_review_registry(review_path)
    metadata = _load_metadata_snapshot(
        _write_metadata_snapshot(
            tmp_path,
            "7EDD",
            "Crystal structure of a serine protease from Streptococcus pyogenes",
            "X-RAY DIFFRACTION",
            2.897,
        )
    )

    rows = _rows_for_target(target, reviews, metadata)

    assert rows[0]["pdb_id"] == "7EDD"
    assert rows[0]["method"] == "X-RAY DIFFRACTION"
    assert rows[0]["resolution_angstrom"] == 2.897
    assert rows[0]["overall_flag"] == "manual_review_required"
    assert rows[0]["chain_coverage"] == "pending manual review"
    assert rows[0]["pocket_definition_status"] == "pending"
    assert rows[0]["docking_readiness"] == "pending"


def test_markdown_report_includes_manual_review_gate_fields():
    report = _markdown_report(
        [
            {
                "target_id": "spycep_scpC",
                "decision_role": "primary",
                "pdb_id": "7EDD",
                "resolution_angstrom": 2.897,
                "overall_flag": "manual_review_required",
                "catalytic_region_status": "present",
                "pocket_definition_status": "unclear",
                "docking_readiness": "pending",
                "review_notes": "Coordinates contain native active-site residues, but pocket definition still needs approval.",
                "notes": "resolution supports initial docking feasibility; manual pocket review required",
            }
        ]
    )

    assert "| Target | Role | PDB | Resolution | Overall | Catalytic | Pocket | Readiness | Review |" in report
    assert "present | unclear | pending" in report
    assert "pocket definition still needs approval" in report
    assert "Pocket boxes are tracked in `docs/methods/pocket_definition.json`." in report
    assert "PDBQT conversion outputs are tracked in `docs/methods/pdbqt_conversion.json`." in report
    assert "PDBQT QC review is tracked in `docs/methods/pdbqt_quality_review.json`." in report


def _write_metadata_snapshot(tmp_path, pdb_id: str, title: str, method: str, resolution: float):
    snapshot_path = tmp_path / "rcsb_metadata.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "source": "RCSB Data API",
                "entries": [
                    {
                        "pdb_id": pdb_id,
                        "title": title,
                        "method": method,
                        "resolution_angstrom": resolution,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return snapshot_path
