"""Source authoritative SMILES + PubChem CID for each seed candidate.

Reads docs/methods/compound_candidates_seed.json (names + class + rationale only)
and, for each name, queries PubChem PUG REST for the CID and SMILES. Nothing here
uses a hand-typed structure: every SMILES comes from PubChem and is canonicalized
with RDKit. Names PubChem cannot resolve are dropped and reported. Writes the
provenance-complete docs/methods/compound_library_source.json.

Run (needs network):
    .\\.venv\\Scripts\\python.exe scripts\\source_compound_library.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.compound_library import validate_smiles

SEED = PROJECT_ROOT / "docs" / "methods" / "compound_candidates_seed.json"
OUTPUT = PROJECT_ROOT / "docs" / "methods" / "compound_library_source.json"
PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/{props}/JSON"
SMILES_PROPS = "IsomericSMILES,CanonicalSMILES,SMILES,ConnectivitySMILES"


def _fetch(name: str) -> dict | None:
    url = PUG.format(name=quote(name), props=SMILES_PROPS)
    try:
        response = requests.get(url, timeout=30)
    except requests.RequestException as exc:  # network error
        print(f"  DROP {name!r}: request error {exc}")
        return None
    if response.status_code != 200:
        print(f"  DROP {name!r}: PubChem HTTP {response.status_code}")
        return None
    props = response.json()["PropertyTable"]["Properties"][0]
    smiles = (
        props.get("IsomericSMILES")
        or props.get("CanonicalSMILES")
        or props.get("SMILES")
        or props.get("ConnectivitySMILES")
    )
    cid = props.get("CID")
    if not smiles or not cid:
        print(f"  DROP {name!r}: no SMILES/CID in PubChem response")
        return None
    if not validate_smiles(smiles):
        print(f"  DROP {name!r}: PubChem SMILES failed RDKit parse")
        return None
    return {"smiles": smiles, "pubchem_cid": cid}


def main() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    resolved: list[dict] = []
    dropped: list[str] = []
    for candidate in seed["candidates"]:
        hit = _fetch(candidate["name"])
        time.sleep(0.25)  # be gentle with PubChem
        if hit is None:
            dropped.append(candidate["name"])
            continue
        resolved.append(
            {
                "ligand_id": candidate["ligand_id"],
                "name": candidate["name"],
                "smiles": hit["smiles"],
                "pubchem_cid": hit["pubchem_cid"],
                "compound_class": candidate["compound_class"],
                "inclusion_rationale": candidate["inclusion_rationale"],
                "source": f"https://pubchem.ncbi.nlm.nih.gov/compound/{hit['pubchem_cid']}",
                "set": candidate["set"],
            }
        )
        print(f"  ok   {candidate['name']:<40} CID {hit['pubchem_cid']}")

    counts: dict[str, int] = {}
    for compound in resolved:
        counts[compound["set"]] = counts.get(compound["set"], 0) + 1

    output = {
        "library_version": "2026-07-02",
        "status": "sourced_from_pubchem_awaiting_user_approval",
        "composition_decision": "both: custom_anti_virulence + fda_comparator",
        "source_of_structures": "PubChem PUG REST (SMILES + CID)",
        "resolved_counts_by_set": counts,
        "dropped_names": dropped,
        "compounds": resolved,
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"\nResolved {len(resolved)} / {len(seed['candidates'])} candidates: {counts}")
    if dropped:
        print(f"Dropped ({len(dropped)}): {', '.join(dropped)}")
    print(f"Wrote {OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
