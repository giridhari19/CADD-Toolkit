from rdkit import Chem
from tkinter import filedialog, Tk
from meeko import MoleculePreparation, PDBQTWriterLegacy
from pathlib import Path

def get_mols(selbatch=0,seldir=0):
	root=Tk()
	root.withdraw()
	if selbatch:
		inp=Path(filedialog.askdirectory( title="Select SDFs directory"))	
	else:
		inp=Path(filedialog.askopenfilename( title ="Select SDF file"))
	if seldir:
		out_dir = Path(filedialog.askdirectory( title="Select Output Folder" ))
	else:
		out_dir=inp.parent / inp.stem if not selbatch else inp / "Result"
		out_dir.mkdir(parents=True, exist_ok=True)
	if selbatch:
		sdfs=list(inp.glob("*.sdf"))
	else:
		sdfs=[inp]
	return sdfs,out_dir

def prep_mol(mol,i):
	preparator=MoleculePreparation()
	mol=Chem.AddHs(mol, addCoords=True)
	cid = mol.GetProp("PUBCHEM_COMPOUND_CID") if mol.HasProp("PUBCHEM_COMPOUND_CID") else "unknown_cid"
	setup=preparator.prepare(mol)[0]
	pdbqt_data=PDBQTWriterLegacy.write_string(setup)
	nameprop=mol.GetProp("_Name").split()[0] if mol.HasProp("_Name") else f"unknown_name_{i}"
	filename=f"{nameprop}_{cid}"
	return pdbqt_data, filename, nameprop

def gen_lig_qt():
	tot=0
	fail=0
	succ=0
	selbatch=input("Batch prep multiple sdfs? Leave blank for no ")
	seldir=input("Select output directory? Leave blank for autogeneration ")
	sdfs,out_dir=get_mols(selbatch,seldir)
	for sdf in sdfs:
		suppl=Chem.SDMolSupplier(sdf)
		for i,mol in enumerate(suppl):
			tot+=1
			if mol is None:
				fail+=1
				continue
			data,filename,molname=prep_mol(mol,i)
			if not data[1]:
				print(f"Failed {molname}")
				print(data[2])
				fail+=1
				continue
			with open(out_dir / f"{filename}.pdbqt", "w") as f:
				f.write(data[0])
				succ+=1
	print(f"Processed: {tot}")
	print(f"Succeeded: {succ}")
	print(f"Failed: {fail}")
