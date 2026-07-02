from pathlib import Path

from spycep_drug_discovery.pdb_summary import box_from_coordinates, coordinates_for_residue, summarize_pdb_file


def test_summarize_pdb_file_reads_core_review_evidence(tmp_path):
    pdb_path = tmp_path / "7EDD.pdb"
    pdb_path.write_text(
        "\n".join(
            [
                "HEADER    LYASE                                   18-MAR-21   7EDD",
                "TITLE     CRYSTAL STRUCTURE OF A TEST PROTEASE",
                "TITLE    2 SECOND TITLE LINE",
                "COMPND    MOL_ID: 1;",
                "COMPND   2 MOLECULE: CHEMOKINE PROTEASE C;",
                "COMPND   3 CHAIN: A, B;",
                "EXPDTA    X-RAY DIFFRACTION",
                "REMARK   2 RESOLUTION.    2.90 ANGSTROMS.",
                "REMARK 465   M RES C SSSEQI",
                "REMARK 465     GLY A    10",
                "REMARK 465     SER A    11",
                "REMARK 465     ASP A    13",
                "REMARK 465     ASN B     5",
                "SEQRES   1 A    5  ALA GLY SER ASP HIS",
                "SEQRES   1 B    3  ASN GLY THR",
                "HET    GOL  A 201       6",
                "HET    MSE  A 202       8",
                "SITE     1 AC1  2 GLY A  10  SER A  11",
                "ATOM      1  N   ALA A   1      11.104  13.207   9.123  1.00 11.11           N",
                "ATOM      2  CA  ALA A   1      12.104  13.207   9.123  1.00 11.11           C",
                "ATOM      3  N   HIS A   4      13.104  13.207   9.123  1.00 11.11           N",
                "ATOM      4  N   ASN B   2      14.104  13.207   9.123  1.00 11.11           N",
                "END",
            ]
        ),
        encoding="utf-8",
    )

    summary = summarize_pdb_file(pdb_path)

    assert summary.pdb_id == "7EDD"
    assert summary.title == "CRYSTAL STRUCTURE OF A TEST PROTEASE SECOND TITLE LINE"
    assert summary.method == "X-RAY DIFFRACTION"
    assert summary.resolution_angstrom == 2.9
    assert summary.seqres_residue_counts == {"A": 5, "B": 3}
    assert summary.atom_residue_counts == {"A": 2, "B": 1}
    assert summary.atom_residue_ranges == {"A": "1, 4", "B": "2"}
    assert summary.missing_residue_counts == {"A": 3, "B": 1}
    assert summary.missing_residue_ranges == {"A": "10-11, 13", "B": "5"}
    assert summary.heterogen_ids == ("GOL", "MSE")
    assert summary.site_ids == ("AC1",)


def test_coordinates_for_residue_reads_atom_and_heterogen_records(tmp_path):
    pdb_path = tmp_path / "pocket.pdb"
    pdb_path.write_text(
        "\n".join(
            [
                "ATOM      1  CA  HIS A 279     -47.070  33.237  23.111  1.00 68.59           C",
                "ATOM      2  NE2 HIS A 279     -44.848  29.504  24.641  1.00 75.26           N",
                "HETATM    3  S   AES A1701     -42.640  27.381  26.413  1.00 82.59           S",
                "HETATM    4  N8  AES A1701     -43.614  26.259  34.311  1.00 59.14           N",
                "END",
            ]
        ),
        encoding="utf-8",
    )

    his_atoms = coordinates_for_residue(pdb_path, chain_id="A", residue_number=279)
    aes_atoms = coordinates_for_residue(
        pdb_path,
        chain_id="A",
        residue_number=1701,
        residue_name="AES",
        include_heterogens=True,
    )

    assert [atom.atom_name for atom in his_atoms] == ["CA", "NE2"]
    assert [atom.atom_name for atom in aes_atoms] == ["S", "N8"]
    assert aes_atoms[0].x == -42.64
    assert aes_atoms[1].z == 34.311


def test_box_from_coordinates_uses_centroid_and_padding():
    box = box_from_coordinates(
        coordinates=[
            (-46.0, 20.0, 10.0),
            (-42.0, 26.0, 22.0),
        ],
        padding_angstrom=4.0,
    )

    assert box.center == (-44.0, 23.0, 16.0)
    assert box.size == (12.0, 14.0, 20.0)


def test_box_from_coordinates_can_enforce_minimum_axis_size():
    box = box_from_coordinates(
        coordinates=[
            (0.0, 0.0, 0.0),
            (2.0, 4.0, 8.0),
        ],
        padding_angstrom=1.0,
        minimum_size_angstrom=12.0,
    )

    assert box.center == (1.0, 2.0, 4.0)
    assert box.size == (12.0, 12.0, 12.0)
