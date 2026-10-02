import molren
import molfetch
import dockprep
import protprep
import dock
import analysis
import subprocess
from tkinter import filedialog, Tk

def end():
	return input("press enter to return to main tool or type 1 to exit> ") == "1"

def main():
	data=""
	while True:
		subprocess.run("clear")
		print(data)
		print("================== CADD TOOLKIT ==================")
		print("Choose the tool you wish to run:")
		print("1. Fetch Molecules from PubChem")
		print("2. SDF Molecule Renaming")
		print("3. Ligand Preparation")
		print("4. Protein Preparation")
		print("5. Docking")
		print("6. Analysis")
		print("7. Exit")
		choice=input("\nEnter number between 1-7\n> ")
		if choice=="2":
			molren.molren()
			if end(): 
				print("Thank you for using the CADD Toolkit. Goodbye!")
				break
		elif choice=="3":
			dockprep.gen_lig_qt()
			if end(): 
				print("Thank you for using the CADD Toolkit. Goodbye!")
				break
		elif choice=="4":
			rep=int(input("Enter number of proteins to be prepared > "))
			for _ in range(rep): 
				protdir=protprep.gen_prot()
				dk=input("Do you want to dock this protein? 1 for yes, blank for no > ").strip()
				if dk=="1":
					dock.dock(dir=protdir)
					ana=input("Do you want to analyze this protein? 1 for yes, blank for no > ").strip()
					if ana=="1":
						analysis.interaction(dir=protdir)
			if end():
				print("Thank you for using the CADD Toolkit. Goodbye!")
				break
		elif choice=="5":
			protdir=dock.dock()
			ana=input("Do you want to analyze this protein? 1 for yes, blank for no > ").strip()
			if ana=="1":
				analysis.interaction(dir=protdir)
			if end():
				print("Thank you for using the CADD Toolkit. Goodbye!")
				break
		elif choice=="6":
			analysis.interaction()
			if end():
				print("Thank you for using the CADD Toolkit. Goodbye!")
				break
		elif choice=="1":
			outdir=molfetch.molfetch()
			nam=input("Do you want to rename the fetched molecules? 1 for yes, blank for no > ").strip()
			if nam=="1":
				molren.molren(dir=outdir)
			if end():
				print("Thank you for using the CADD Toolkit. Goodbye!")
				break
		elif choice=="7":
			print("Thank you for using the CADD Toolkit. Goodbye!")
			break
		else:
			print("Invalid Choice")
			if end():
				print("Thank you for using the CADD Toolkit. Goodbye!")
				break
	
		
if __name__=="__main__":
	main()