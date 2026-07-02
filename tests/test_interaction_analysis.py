from spycep_drug_discovery.interaction_analysis import (
    active_site_residue_keys,
    analyze_pose_interactions,
    contact_residue_keys,
    parse_pdbqt_atoms,
)


ACTIVE_SITE = [
    {"chain_id": "A", "residue_name": "ASP", "residue_number": 151},
    {"chain_id": "A", "residue_name": "HIS", "residue_number": 279},
    {"chain_id": "A", "residue_name": "SER", "residue_number": 617},
]


def _atom(atom_name, res_name, res_num, x, y, z, element="C"):
    return (
        f"ATOM      1 {atom_name:>4} {res_name:>3} A{res_num:4d}"
        f"    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00     0.000 {element:>2}"
    )


def test_parse_pdbqt_atoms_first_model_only():
    text = "\n".join(
        [
            "MODEL 1",
            _atom("OG", "SER", 617, 0.0, 0.0, 0.0),
            "ENDMDL",
            "MODEL 2",
            _atom("OG", "SER", 617, 99.0, 99.0, 99.0),
            "ENDMDL",
        ]
    )

    atoms = parse_pdbqt_atoms(text, first_model_only=True)

    assert len(atoms) == 1
    assert atoms[0].residue_key == "A:617:SER"


def test_contact_residue_keys_within_cutoff():
    receptor = parse_pdbqt_atoms(
        "\n".join(
            [
                _atom("OG", "SER", 617, 0.0, 0.0, 0.0),
                _atom("ND1", "HIS", 279, 20.0, 20.0, 20.0),
            ]
        )
    )
    ligand = parse_pdbqt_atoms("\n".join([_atom("C1", "LIG", 900, 1.5, 0.0, 0.0)]))

    contacts = contact_residue_keys(receptor, ligand, cutoff=4.0)

    assert contacts == ["A:617:SER"]


def test_analyze_pose_interactions_flags_active_site(tmp_path):
    receptor_path = tmp_path / "receptor.pdbqt"
    pose_path = tmp_path / "pose.pdbqt"
    receptor_path.write_text(
        "\n".join(
            [
                _atom("OD1", "ASP", 151, 0.0, 0.0, 0.0),
                _atom("NE2", "HIS", 279, 10.0, 0.0, 0.0),
                _atom("OG", "SER", 617, 20.0, 0.0, 0.0),
                _atom("CA", "GLY", 400, 50.0, 50.0, 50.0),
            ]
        ),
        encoding="utf-8",
    )
    pose_path.write_text(
        "\n".join(["MODEL 1", _atom("C1", "LIG", 900, 10.0, 1.0, 0.0), "ENDMDL"]),
        encoding="utf-8",
    )

    result = analyze_pose_interactions(receptor_path, pose_path, ACTIVE_SITE, cutoff=4.0)

    assert "A:279:HIS" in result["contacted_active_site_residues"]
    assert "A:400:GLY" not in result["contacted_active_site_residues"]
    assert result["contacts_catalytic_triad"] is False
    assert result["best_pose_ligand_atom_count"] == 1


def test_active_site_residue_keys():
    assert active_site_residue_keys(ACTIVE_SITE) == ["A:151:ASP", "A:279:HIS", "A:617:SER"]
