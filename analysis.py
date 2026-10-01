from pathlib import Path
from dock import seldir
import subprocess
from rdkit import Chem
from Bio.PDB import PDBParser, PDBIO

def sdf_to_pdb(dir=None):
	if dir is None:
		protdir,protid=seldir()
	else:
		protdir=Path(dir)
		protid=protdir.stem
	sdff=protdir / "docked" / "sdf files"
	sdfs=list(sdff.glob("*.sdf"))
	pdbf=protdir / "docked" / "pdb files"
	pdbf.mkdir(parents=True, exist_ok=True)
	print("Converting SDF files to PDB files")
	for sdf in sdfs:
		nameinfo=sdf.stem.split("_")
		suppl=Chem.SDMolSupplier(sdf)
		for i,mol in enumerate(suppl):
			if i>1: break
			if mol is None:
				print(f"Invalid molecule at index {i} for molecule {nameinfo[0]}")
				continue
			Chem.MolToPDBFile(mol, pdbf / f"{nameinfo[0]}_{nameinfo[1]}_pose_{i}.pdb")
	print("Successfully converted SDF files to PDB files")
	payload=[
		"pdb2pqr",
		"--ff=AMBER",
	]
	ph=input("Enter pH for pH based protonation. Leave blank for non-protonated H addition (usually 7.4 for physiological conditions) > ").strip()
	if ph: payload.extend(["--titration-state-method=propka",f"--with-ph={ph}"])
	payload.extend([
		f"{protid}.pdb",
		f"{protid}.pqr",
		"--pdb-output", f"{protid}_h.pdb"
	])
	subprocess.run(payload, cwd=protdir, check=True)
	subprocess.run(["rm", f"{protid}.pqr"], cwd=protdir, check=True)
	return protdir,protid,pdbf

def merge_pdb(dir=None):
	protdir,protid,pdbf=sdf_to_pdb(dir)
	prot= protdir / f"{protid}_h.pdb"
	parser=PDBParser(QUIET=True)
	ligs=list(pdbf.glob("*.pdb"))
	print("Creating complex structure of ligand and receptor")
	for lig in ligs:
		protstr=parser.get_structure("protein", prot)
		protmodel=protstr[0]
		filename=lig.stem
		ligstr=parser.get_structure("ligand", lig)
		ligmodel=ligstr[0]
		ligchain=list(ligmodel.get_chains())[0]
		ligchain.id="Z"
		protmodel.add(ligchain)
		io=PDBIO()
		io.set_structure(protstr)
		cxdir=protdir / "docked" / "complexes"
		(cxdir).mkdir(parents=True, exist_ok=True)
		io.save(str(cxdir / f"{filename}_complex.pdb"))
	print("Successfully created complex structures")
	return protdir,cxdir,protid

def interaction(dir=None):
	protdir,cxdir,protid=merge_pdb(dir)
	cwd=protdir / "interactions"
	cwd.mkdir(parents=True, exist_ok=True)
	pdbs=list(cxdir.glob("*.pdb"))
	for pdb in pdbs:
		fileid="_".join(pdb.stem.split("_")[:2])
		outdir= cwd / fileid
		outdir.mkdir(parents=True, exist_ok=True)
	for idir in cwd.glob("*_*"):
		if idir.is_dir():
			filename=idir.stem
			pdbfiles=list(cxdir.glob(f"{filename}_*.pdb"))
			for pdbfile in pdbfiles:
				pose=list(pdbfile.stem.split("_"))[3]
				actualcwd= idir / f"pose {pose}"
				actualcwd.mkdir(parents=True, exist_ok=True)
				result = subprocess.run([
				"plip",
				"-f", pdbfile,
				"--nohydro",
				"-xtp"
				], cwd=actualcwd)
				if result.returncode != 0:
					print(f"Error occurred while running PLIP for {pdbfile}: {result.stderr}")
	script_path = Path(__file__).resolve().parent / "pose0interaction.sh"
	subprocess.run([
		"bash", str(script_path)
	], cwd=protdir / "interactions")
	subprocess.run([
		"cp", protdir / "docked" / f"{protid}_useful.csv",
		protdir / "interactions" / "pose0 files" / f"{protid}_useful.csv"

	])
	