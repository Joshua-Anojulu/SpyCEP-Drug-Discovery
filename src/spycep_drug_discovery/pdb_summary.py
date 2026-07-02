from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


POLYMER_HET_RESIDUES = frozenset({"MSE", "SEC", "PYL"})


@dataclass(frozen=True)
class PdbFileSummary:
    pdb_id: str
    title: str
    method: str
    resolution_angstrom: float | None
    seqres_residue_counts: dict[str, int]
    atom_residue_counts: dict[str, int]
    atom_residue_ranges: dict[str, str]
    missing_residue_counts: dict[str, int]
    missing_residue_ranges: dict[str, str]
    heterogen_ids: tuple[str, ...]
    site_ids: tuple[str, ...]


@dataclass(frozen=True)
class AtomCoordinate:
    record_name: str
    atom_name: str
    residue_name: str
    chain_id: str
    residue_number: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class CoordinateBox:
    center: tuple[float, float, float]
    size: tuple[float, float, float]


def summarize_pdb_file(path: Path) -> PdbFileSummary:
    title_parts: list[str] = []
    pdb_id = path.stem.upper()
    method = ""
    resolution_angstrom: float | None = None
    seqres_counts: dict[str, int] = {}
    atom_residues: dict[str, set[int]] = {}
    missing_residues: dict[str, set[int]] = {}
    heterogen_ids: list[str] = []
    site_ids: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("HEADER"):
            pdb_id = _pdb_id_from_header(line, fallback=pdb_id)
        elif line.startswith("TITLE"):
            title = line[10:].strip()
            if title:
                title_parts.append(title)
        elif line.startswith("EXPDTA"):
            method = line[10:].strip()
        elif line.startswith("REMARK   2 RESOLUTION."):
            resolution_angstrom = _parse_resolution(line)
        elif line.startswith("SEQRES"):
            _record_seqres_count(line, seqres_counts)
        elif line.startswith("ATOM  ") or _is_polymer_hetatm(line):
            _record_coordinate_residue(line, atom_residues)
        elif line.startswith("REMARK 465"):
            _record_missing_residue(line, missing_residues)
        elif line.startswith("HET   "):
            _append_unique(line.split()[1], heterogen_ids)
        elif line.startswith("SITE  "):
            parts = line.split()
            if len(parts) >= 3:
                _append_unique(parts[2], site_ids)

    return PdbFileSummary(
        pdb_id=pdb_id,
        title=" ".join(title_parts),
        method=method,
        resolution_angstrom=resolution_angstrom,
        seqres_residue_counts=dict(sorted(seqres_counts.items())),
        atom_residue_counts={chain: len(residues) for chain, residues in sorted(atom_residues.items())},
        atom_residue_ranges={chain: _format_ranges(residues) for chain, residues in sorted(atom_residues.items())},
        missing_residue_counts={chain: len(residues) for chain, residues in sorted(missing_residues.items())},
        missing_residue_ranges={chain: _format_ranges(residues) for chain, residues in sorted(missing_residues.items())},
        heterogen_ids=tuple(heterogen_ids),
        site_ids=tuple(site_ids),
    )


def coordinates_for_residue(
    path: Path,
    chain_id: str,
    residue_number: int,
    residue_name: str | None = None,
    include_heterogens: bool = False,
) -> tuple[AtomCoordinate, ...]:
    coordinates: list[AtomCoordinate] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not _is_coordinate_record(line, include_heterogens=include_heterogens):
            continue
        atom = _parse_atom_coordinate(line)
        if atom is None:
            continue
        if atom.chain_id != chain_id or atom.residue_number != residue_number:
            continue
        if residue_name is not None and atom.residue_name != residue_name:
            continue
        coordinates.append(atom)
    return tuple(coordinates)


def box_from_coordinates(
    coordinates: tuple[AtomCoordinate, ...] | list[AtomCoordinate] | tuple[tuple[float, float, float], ...] | list[tuple[float, float, float]],
    padding_angstrom: float,
    minimum_size_angstrom: float | None = None,
) -> CoordinateBox:
    points = [_coordinate_tuple(coordinate) for coordinate in coordinates]
    if not points:
        raise ValueError("Cannot compute coordinate box without at least one coordinate.")
    min_x, max_x = _min_max(point[0] for point in points)
    min_y, max_y = _min_max(point[1] for point in points)
    min_z, max_z = _min_max(point[2] for point in points)
    return CoordinateBox(
        center=(
            _round_coordinate((min_x + max_x) / 2),
            _round_coordinate((min_y + max_y) / 2),
            _round_coordinate((min_z + max_z) / 2),
        ),
        size=tuple(
            _round_coordinate(_apply_minimum_size(size, minimum_size_angstrom))
            for size in (
                (max_x - min_x) + (padding_angstrom * 2),
                (max_y - min_y) + (padding_angstrom * 2),
                (max_z - min_z) + (padding_angstrom * 2),
            )
        ),
    )


def _pdb_id_from_header(line: str, fallback: str) -> str:
    fixed_width_id = line[62:66].strip()
    if fixed_width_id:
        return fixed_width_id.upper()
    parts = line.split()
    return parts[-1].upper() if parts else fallback


def _parse_resolution(line: str) -> float | None:
    match = re.search(r"RESOLUTION\.\s+([0-9.]+)\s+ANGSTROMS", line)
    return float(match.group(1)) if match else None


def _record_seqres_count(line: str, counts: dict[str, int]) -> None:
    parts = line.split()
    if len(parts) < 4:
        return
    chain = parts[2]
    try:
        counts[chain] = int(parts[3])
    except ValueError:
        return


def _is_polymer_hetatm(line: str) -> bool:
    if not line.startswith("HETATM"):
        return False
    return line[17:20].strip() in POLYMER_HET_RESIDUES


def _is_coordinate_record(line: str, include_heterogens: bool) -> bool:
    return line.startswith("ATOM  ") or (include_heterogens and line.startswith("HETATM"))


def _parse_atom_coordinate(line: str) -> AtomCoordinate | None:
    residue_number = _parse_residue_number(line[22:27])
    if residue_number is None:
        return None
    try:
        x = float(line[30:38])
        y = float(line[38:46])
        z = float(line[46:54])
    except ValueError:
        return None
    return AtomCoordinate(
        record_name=line[0:6].strip(),
        atom_name=line[12:16].strip(),
        residue_name=line[17:20].strip(),
        chain_id=line[21].strip() or "?",
        residue_number=residue_number,
        x=x,
        y=y,
        z=z,
    )


def _record_coordinate_residue(line: str, residues_by_chain: dict[str, set[int]]) -> None:
    chain = line[21].strip() or "?"
    residue_number = _parse_residue_number(line[22:27])
    if residue_number is None:
        return
    residues_by_chain.setdefault(chain, set()).add(residue_number)


def _record_missing_residue(line: str, residues_by_chain: dict[str, set[int]]) -> None:
    parts = line.split()
    if len(parts) < 5:
        return
    if _looks_like_residue(parts[2]):
        chain_index = 3
        sequence_index = 4
    elif len(parts) >= 6 and _looks_like_residue(parts[3]):
        chain_index = 4
        sequence_index = 5
    else:
        return

    residue_number = _parse_residue_number(parts[sequence_index])
    if residue_number is None:
        return
    residues_by_chain.setdefault(parts[chain_index], set()).add(residue_number)


def _looks_like_residue(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z0-9]{2}", value))


def _parse_residue_number(value: str) -> int | None:
    match = re.match(r"\s*(-?\d+)", value)
    return int(match.group(1)) if match else None


def _append_unique(value: str, values: list[str]) -> None:
    if value not in values:
        values.append(value)


def _coordinate_tuple(coordinate: AtomCoordinate | tuple[float, float, float]) -> tuple[float, float, float]:
    if isinstance(coordinate, AtomCoordinate):
        return coordinate.x, coordinate.y, coordinate.z
    return coordinate


def _min_max(values) -> tuple[float, float]:
    ordered = list(values)
    return min(ordered), max(ordered)


def _round_coordinate(value: float) -> float:
    return round(value, 3)


def _apply_minimum_size(size: float, minimum_size: float | None) -> float:
    if minimum_size is None:
        return size
    return max(size, minimum_size)


def _format_ranges(residues: set[int]) -> str:
    if not residues:
        return ""
    ranges: list[str] = []
    ordered = sorted(residues)
    start = previous = ordered[0]
    for residue in ordered[1:]:
        if residue == previous + 1:
            previous = residue
            continue
        ranges.append(_format_range(start, previous))
        start = previous = residue
    ranges.append(_format_range(start, previous))
    return ", ".join(ranges)


def _format_range(start: int, end: int) -> str:
    return str(start) if start == end else f"{start}-{end}"
