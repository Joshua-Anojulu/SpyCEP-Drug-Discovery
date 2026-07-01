from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


RCSB_ENTRY_URL = "https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
RCSB_PDB_DOWNLOAD_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"


@dataclass(frozen=True)
class RcsbEntryMetadata:
    pdb_id: str
    title: str
    method: str
    resolution_angstrom: float | None

    def to_json_dict(self) -> dict[str, str | float | None]:
        return asdict(self)


def normalize_entry_metadata(raw: dict[str, Any]) -> RcsbEntryMetadata:
    resolutions = raw.get("rcsb_entry_info", {}).get("resolution_combined") or []
    resolution = float(resolutions[0]) if resolutions else None
    experiments = raw.get("exptl") or [{}]
    return RcsbEntryMetadata(
        pdb_id=str(raw.get("rcsb_id", "")).upper(),
        title=str(raw.get("struct", {}).get("title", "")),
        method=str(experiments[0].get("method", "")),
        resolution_angstrom=resolution,
    )


def fetch_entry_metadata(pdb_id: str, timeout_seconds: int = 30) -> RcsbEntryMetadata:
    import requests

    response = requests.get(RCSB_ENTRY_URL.format(pdb_id=pdb_id.upper()), timeout=timeout_seconds)
    response.raise_for_status()
    return normalize_entry_metadata(response.json())


def fetch_pdb_text(pdb_id: str, timeout_seconds: int = 30) -> str:
    import requests

    response = requests.get(RCSB_PDB_DOWNLOAD_URL.format(pdb_id=pdb_id.upper()), timeout=timeout_seconds)
    response.raise_for_status()
    return response.text
