import subprocess
from pathlib import Path
from tkinter import filedialog, Tk
def gen_prot():
	root=Tk()
	root.withdraw()
	print("Ensure protein and its co-crystallized ligand are present in the same directory(named as protein's pdb id) and protein is named its pdb_id.pdb and ligand pdb_idlig.sdf")
	protdir=Path(filedialog.askdirectory(title="Select Protein Directory"))
	protid=protdir.stem
	print(protid)
	pad=input("Enter padding size (recommended 5) > ")
	payload=[
		"mk_prepare_receptor.py" , 
		"--read_pdb", f"{protid}.pdb",
		"-o", protid,
		"-p", "-v",
		"--box_enveloping", f"{protid}lig.sdf",
		"--padding", pad
		]
	defaltloc1=input("Value for default altloc. Leave blank if not needed > ").strip()
	print("Format for wanted altloc: CHAIN:INDEX1,INDEX2,...=altloc1,CHAIN1...=altloc2,...")
	wntaltloc1=input("Value for wanted altloc. Leave blank for no wanted altloc > ").strip()
	if defaltloc1: payload.extend(["--default_altloc", defaltloc1])
	if wntaltloc1: payload.extend(["--wanted_altloc", wntaltloc1])
	result=subprocess.run(payload, cwd=protdir, capture_output=True, text=True)
	print(result.stdout)
	if result.returncode!=0 and "alternate location" in result.stdout:
		print("Open the pdb file in notepad and find out the altlocs of the given residues.\nIf most residues have highest occupancy in a certain altloc, use that as default altloc and set the outliers using wanted altloc")
		defaltloc=input("Value for default altloc. Leave blank if not needed > ").strip()
		print("Format for wanted altloc: CHAIN:INDEX1,INDEX2,...=altloc1,CHAIN1...=altloc2,...")
		wntaltloc=input("Value for wanted altloc. Leave blank for no wanted altloc > ").strip()
		if defaltloc: payload.extend(["--default_altloc", defaltloc])
		if wntaltloc: payload.extend(["--wanted_altloc", wntaltloc])
		subprocess.run(payload, cwd=protdir)
	return protdir