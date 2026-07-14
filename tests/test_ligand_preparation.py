import pytest

from spycep_drug_discovery.ligand_preparation import (
    LigandPreparationError,
    docked_species_smiles,
    heavy_atom_count,
    prepare_ligand,
    protonate_at_ph,
    smiles_to_sdf,
    undefined_stereocenters,
)


def test_heavy_atom_count_strips_salts():
    # ethylamine hydrochloride: organic fragment has 3 heavy atoms, chloride is dropped.
    assert heavy_atom_count("CCN.Cl") == 3


def test_protonation_makes_amidine_cationic_at_physiological_ph():
    # Benzamidine (amidine pKa ~11.6) is an amidinium cation at pH 7.4. The S1 salt
    # bridge is the binding rationale for this chemotype, so the neutral form is wrong.
    from rdkit import Chem

    protonated = protonate_at_ph("NC(=N)c1ccccc1", ph=7.4)

    assert Chem.GetFormalCharge(Chem.MolFromSmiles(protonated)) == 1


def test_protonation_makes_carboxylic_acid_anionic_at_physiological_ph():
    from rdkit import Chem

    protonated = protonate_at_ph("CC(=O)Oc1ccccc1C(=O)O", ph=7.4)  # aspirin

    assert Chem.GetFormalCharge(Chem.MolFromSmiles(protonated)) == -1


def test_docked_species_desalts_before_protonating():
    from rdkit import Chem

    species = docked_species_smiles("NC(=N)c1ccccc1.Cl")
    mol = Chem.MolFromSmiles(species)

    assert len(Chem.GetMolFrags(mol)) == 1
    assert Chem.GetFormalCharge(mol) == 1


def test_heavy_atom_count_is_unchanged_by_protonation():
    # Protonation adds hydrogens only, so the ligand-efficiency denominator must not move.
    assert heavy_atom_count("NC(=N)c1ccccc1") == 9


def test_undefined_stereocenters_are_reported():
    # Ibuprofen's alpha carbon is unspecified in the PubChem SMILES; ETKDG would pick
    # one arbitrarily, so preparation must surface it rather than hide it.
    assert undefined_stereocenters("CC(C)Cc1ccc(cc1)C(C)C(=O)O") == [10]
    assert undefined_stereocenters("NC(=N)c1ccccc1") == []


def test_smiles_to_sdf_records_the_species_actually_docked(tmp_path):
    out = tmp_path / "benzamidine.sdf"

    record = smiles_to_sdf("NC(=N)c1ccccc1.Cl", out, seed=42)

    assert record["formal_charge"] == 1
    assert record["protonation_ph"] == 7.4
    assert record["heavy_atom_count"] == 9
    assert record["mmff_converged"] is True
    assert "Cl" not in out.read_text()


def test_smiles_to_sdf_is_deterministic(tmp_path):
    first = tmp_path / "a.sdf"
    second = tmp_path / "b.sdf"

    a = smiles_to_sdf("NC(=N)c1ccccc1", first, seed=42)
    b = smiles_to_sdf("NC(=N)c1ccccc1", second, seed=42)

    assert a["embedded_isomeric_smiles"] == b["embedded_isomeric_smiles"]
    assert first.read_text() == second.read_text()


def test_smiles_to_sdf_refuses_ligands_mmff_cannot_parameterise(tmp_path):
    # MMFF94 has no boron parameters. Previously this silently emitted an unoptimised
    # ETKDG geometry as if it were a prepared ligand.
    with pytest.raises(LigandPreparationError, match="MMFF94"):
        smiles_to_sdf("B(C1=CC=CC=C1)(O)O", tmp_path / "boron.sdf", seed=42)


def test_smiles_to_sdf_rejects_bad_smiles(tmp_path):
    with pytest.raises(LigandPreparationError):
        smiles_to_sdf("not-a-smiles(((", tmp_path / "x.sdf")


def test_prepare_ligand_raises_when_meeko_fails(tmp_path):
    compound = {"ligand_id": "benzamidine", "smiles": "NC(=N)c1ccccc1", "role": "positive"}

    with pytest.raises(LigandPreparationError):
        prepare_ligand(
            compound,
            project_root=tmp_path,
            work_dir=tmp_path / "work",
            output_dir=tmp_path / "out",
            # a command that runs but never writes the -o PDBQT file
            meeko_command=["python", "-c", "pass"],
        )


def test_prepare_ligand_does_not_report_a_stale_pdbqt_as_this_runs_output(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    stale = out_dir / "benzamidine__state_01.pdbqt"
    stale.write_text("ATOM  stale pose from a previous run\n", encoding="utf-8")
    compound = {"ligand_id": "benzamidine", "smiles": "NC(=N)c1ccccc1"}

    with pytest.raises(LigandPreparationError):
        prepare_ligand(
            compound,
            project_root=tmp_path,
            work_dir=tmp_path / "work",
            output_dir=out_dir,
            meeko_command=["python", "-c", "pass"],  # exits 0, writes nothing
        )

    assert not stale.exists()


def test_catalog_backed_ambiguous_states_are_consumed_verbatim():
    import json
    from rdkit import Chem

    catalog = json.loads(open("docs/methods/species_audit.json", encoding="utf-8").read())
    source = next(
        row["source_smiles"]
        for row in catalog["states"]
        if row["entity_id"] == "amoxicillin"
    )
    neutral = docked_species_smiles(
        source,
        entity_id="amoxicillin",
        state_id="alpha_amine_neutral",
        species_catalog=catalog,
    )
    ammonium = docked_species_smiles(
        source,
        entity_id="amoxicillin",
        state_id="alpha_ammonium",
        species_catalog=catalog,
    )

    assert Chem.GetFormalCharge(Chem.MolFromSmiles(neutral)) == -1
    assert Chem.GetFormalCharge(Chem.MolFromSmiles(ammonium)) == 0
    assert neutral != ammonium


def test_smiles_to_sdf_records_mmff94s_cap_and_separate_stereo_evidence(tmp_path):
    out = tmp_path / "ibuprofen.sdf"
    record = smiles_to_sdf("CC(C)Cc1ccc(cc1)C(C)C(=O)O", out, seed=42)

    assert record["mmff_variant"] == "MMFF94s"
    assert record["mmff_max_iterations"] == 2000
    assert record["mmff_status"] == 0
    assert record["mmff_converged"] is True
    assert record["source_undefined_centers"] == [10]
    assert record["embedded_unassigned_centers"] == []
    assert "@" in record["embedded_isomeric_smiles"]


def test_prepare_ligand_filenames_include_entity_and_state(tmp_path):
    compound = {
        "entity_id": "amoxicillin",
        "state_id": "alpha_ammonium",
        "smiles": "CC",
    }

    with pytest.raises(LigandPreparationError):
        prepare_ligand(
            compound,
            project_root=tmp_path,
            work_dir=tmp_path / "work",
            output_dir=tmp_path / "out",
            meeko_command=["python", "-c", "pass"],
        )

    assert (tmp_path / "work" / "amoxicillin__alpha_ammonium.sdf").is_file()
    assert not (tmp_path / "out" / "amoxicillin__alpha_ammonium.pdbqt").exists()
