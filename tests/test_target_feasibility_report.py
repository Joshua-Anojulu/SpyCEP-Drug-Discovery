import json

from scripts.analyze_target_feasibility import _rows_for_target
from spycep_drug_discovery.targets import StructureCandidate, Target


def test_rows_for_target_reads_normalized_cached_rcsb_metadata(tmp_path):
    metadata_dir = tmp_path / "data" / "raw" / "rcsb"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "7EDD.json").write_text(
        json.dumps(
            {
                "pdb_id": "7EDD",
                "title": "Crystal structure of a serine protease from Streptococcus pyogenes",
                "method": "X-RAY DIFFRACTION",
                "resolution_angstrom": 2.897,
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

    rows = _rows_for_target(tmp_path, target)

    assert rows[0]["pdb_id"] == "7EDD"
    assert rows[0]["method"] == "X-RAY DIFFRACTION"
    assert rows[0]["resolution_angstrom"] == 2.897
    assert rows[0]["overall_flag"] == "candidate"
