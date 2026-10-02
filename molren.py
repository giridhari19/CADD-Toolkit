from dock import seldir
from pathlib import Path
import subprocess
from rdkit import Chem
import requests
import time

def molren(dir=None):
    if dir is None:
        moldir,junk=seldir(title="Select SDF Directory")
    else:
        moldir=Path(dir)
    outdir=seldir(title="Select Output Directory")[0]
    request_interval= 1 / 5
    next_request = time.monotonic()
    for mol in moldir.glob("*.sdf"):
        suppl=Chem.SDMolSupplier(str(mol))
        for m in suppl:
            if m is None: continue
            if m.HasProp("PUBCHEM_COMPOUND_CID"):
                cid=m.GetProp("PUBCHEM_COMPOUND_CID")
            elif m.HasProp("_Name"):
                cid=m.GetProp("_Name")
            else:
                print(f"Warning: No CID or Name found for molecule in {mol}. Skipping.")
                continue
            wait_time = next_request - time.monotonic()
            if wait_time > 0:
                time.sleep(wait_time)
            next_request = time.monotonic() + request_interval
            url=f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON"
            for attempt in range(3):
                response=requests.get(url, timeout=30)
                if response.status_code != 502 or attempt == 2:
                    break
                time.sleep(1)
            if response.status_code==200:
                data=response.json()
                synonym=data["InformationList"]["Information"][0]["Synonym"][0]
                synonym=synonym.replace("_", "-")
                if synonym:
                    print(f"Renaming molecule with CID {cid} to {synonym}")
                    m.SetProp("_Name", synonym)
                    output_path=outdir / f"{synonym}_CID_{cid}.sdf"
                    writer=Chem.SDWriter(str(output_path))
                    writer.write(m)
                else:
                    print(f"Warning: No synonym found for CID {cid}. Skipping.")
            else:
                print(f"Warning: Failed to fetch synonym for CID {cid}.\n{response.text}")
                m.SetProp("_Name", f"{cid}")
                output_path=outdir / f"UnknownName_CID_{cid}.sdf"
                writer=Chem.SDWriter(str(output_path))
                writer.write(m)
    writer.close()
    print(f"Renaming complete. Renamed files are saved in {outdir}")