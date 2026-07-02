"""Validate the tracked compound-library source and write a summary manifest.

Reads docs/methods/compound_library_source.json (the scientific record, with
per-compound provenance), validates every entry (required fields, valid set,
PMID/URL source, parseable SMILES, unique ids/names), and writes a summary to
docs/methods/compound_library.json. Fails loudly on any incomplete provenance.

Run:
    .\\.venv\\Scripts\\python.exe scripts\\curate_compounds.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.admet import admet_profile
from spycep_drug_discovery.compound_library import load_compound_library, summarize_library

SOURCE = PROJECT_ROOT / "docs" / "methods" / "compound_library_source.json"
MANIFEST = PROJECT_ROOT / "docs" / "methods" / "compound_library.json"


def main() -> None:
    data = load_compound_library(SOURCE)
    compounds = data.get("compounds", [])
    summary = summarize_library(compounds)
    summary["source"] = "docs/methods/compound_library_source.json"

    rows = []
    drug_like = 0
    for compound in compounds:
        profile = admet_profile(compound["smiles"])
        drug_like += int(profile["drug_like"])
        rows.append(
            {
                "ligand_id": compound["ligand_id"],
                "name": compound["name"],
                "set": compound["set"],
                "compound_class": compound["compound_class"],
                "pubchem_cid": compound.get("pubchem_cid"),
                "source": compound["source"],
                "molecular_weight": profile["descriptors"]["molecular_weight"],
                "logp": profile["descriptors"]["logp"],
                "lipinski_passes": profile["lipinski"]["passes"],
                "veber_passes": profile["veber"]["passes"],
                "pains_alerts": profile["pains_alerts"],
                "drug_like": profile["drug_like"],
            }
        )
    summary["drug_like_count"] = drug_like
    summary["compounds"] = rows

    MANIFEST.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Validated {summary['compound_count']} compounds: {summary['counts_by_set']}")
    print(f"Drug-like (Lipinski+Veber, no PAINS): {drug_like}/{summary['compound_count']}")
    print(f"Wrote {MANIFEST.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
