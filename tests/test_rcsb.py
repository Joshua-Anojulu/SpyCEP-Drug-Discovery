from spycep_drug_discovery.rcsb import RcsbEntryMetadata, normalize_entry_metadata


def test_normalize_entry_metadata_extracts_resolution_and_method():
    raw = {
        "rcsb_id": "7EDD",
        "struct": {"title": "Crystal structure of a serine protease from Streptococcus pyogenes"},
        "exptl": [{"method": "X-RAY DIFFRACTION"}],
        "rcsb_entry_info": {"resolution_combined": [2.897]},
    }

    metadata = normalize_entry_metadata(raw)

    assert metadata == RcsbEntryMetadata(
        pdb_id="7EDD",
        title="Crystal structure of a serine protease from Streptococcus pyogenes",
        method="X-RAY DIFFRACTION",
        resolution_angstrom=2.897,
    )


def test_normalize_entry_metadata_handles_missing_resolution():
    raw = {
        "rcsb_id": "XXXX",
        "struct": {"title": "Predicted or unresolved entry"},
        "exptl": [{"method": "ELECTRON MICROSCOPY"}],
        "rcsb_entry_info": {},
    }

    metadata = normalize_entry_metadata(raw)

    assert metadata.pdb_id == "XXXX"
    assert metadata.resolution_angstrom is None
