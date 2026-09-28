from pathlib import Path
import subprocess
from tkinter import filedialog, Tk
import pandas as pd
from Bio.PDB import PDBParser

def seldir(title="Select Protein Directory"):
	root=Tk()
	root.withdraw()
	protdir=Path(filedialog.askdirectory(title=title))
	protid=protdir.stem
	return protdir,protid

def dock():
	protdir,protid=seldir()
	print("Ensure ligands are present in folder named 'ligands' in the same directory as protein")
	(protdir / "docked").mkdir(parents=True, exist_ok=True)
	exh=input("Enter exhaustiveness value. Leave blank for 8 > ").strip()
	nmod=input("Enter num modes value. Leave blank for 9 > ").strip()
	enrag=input("Enter energy range value. Leave blank for 3 > ").strip()
	payload=[
		"vina", 
		"--receptor", f"{protid}.pdbqt",
		"--config", f"{protid}.box.txt",
		"--batch", "ligands",
		"--dir", "docked",
		"--verbosity", "2"
		]
	if exh: payload.extend(["--exhaustiveness", exh])
	if nmod: payload.extend(["--num_modes", nmod])
	if enrag: payload.extend(["--energy_range", enrag])
	with open(protdir / "docking.log", "w") as log:
		process=subprocess.Popen(payload, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=protdir)
		while True:
			char=process.stdout.read(1)
			if not char: break
			print(char, end="",flush=True)
			log.write(char)
		process.wait()

	pdbqts=list((protdir / "docked").glob("*.pdbqt"))
	results=[]
	for file in pdbqts:
		nameinfo=file.stem.split("_")
		if nameinfo[1].isdigit():
			with open(file) as f:
				lines=f.readlines()
			val=[]
			for line in lines:
				if "REMARK VINA RESULT:" in line:
					val.append(line.split()[3])
			val=list(map(float, val))
			best=min(val)
			pose=val.index(best) +1
			record = {
				"Name": nameinfo[0],
				"CID": nameinfo[1],
				"Affinity": best,
				"Pose": pose
				}
			results.append(record)	
	df=pd.DataFrame(results)
	df=df.sort_values("Affinity").reset_index(drop=True)
	print("",df,"",sep='\n')
	ediff=float(input("Enter energy difference for comparision with best energy as reference > "))
	df.to_csv(protdir / "docked" / f"{protid}_results.csv", index=False)
	max=min(df['Affinity'])
	top=df[df['Affinity'] <= max+ediff]
	top=top[['Name','CID','Affinity']]
	print(top)
	top.to_csv(protdir / "docked" / f"{protid}_useful.csv", index=False)
	sdff=protdir / "docked" / "sdf files"
	sdff.mkdir(parents=True, exist_ok=True)
	qts=list((protdir / "docked").glob("*.pdbqt"))
	print("Exporting generated pdbqt files as sdf")
	subprocess.run([
		"mk_export.py",
		*qts, 
		"--suffix", "_docked"
		], cwd=sdff, check=True)
	print("Exported Successfully!")