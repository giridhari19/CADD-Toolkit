from dock import seldir,selfile
from pathlib import Path
import time
import requests
import csv

def molfetch_cid(vals,outdir):
    request_interval = 1 / 5
    next_request = time.monotonic()
    for cid in vals:
        cid=cid.strip()
        wait_time = next_request - time.monotonic()
        if wait_time > 0:
            time.sleep(wait_time)
        next_request = time.monotonic() + request_interval
        url=f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/SDF?record_type=3d"
        print(f"Fetching SDF for CID {cid} from {url}")
        for attempt in range(3):
            response=requests.get(url, timeout=30)
            if response.status_code != 502 or attempt == 2:
                break
            time.sleep(1)
        if response.status_code==200:
            sdf_path=outdir / f"{cid}.sdf"  
            with open(sdf_path, "wb") as f:
                f.write(response.content)
            print(f"Downloaded SDF for CID {cid}")
        else:
            print(f"Failed to fetch SDF for CID {cid}. HTTP Status Code: {response.status_code}")
    print(f"Fetching complete. SDF files are saved in {outdir}")

def molfetch_smiles(vals,outdir):
    request_interval = 1 / 5
    next_request = time.monotonic()
    for smiles in vals:
        smiles=smiles.strip()
        url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/cids/TXT"
        payload= {"smiles": smiles}
        wait_time = next_request - time.monotonic()
        if wait_time > 0:
            time.sleep(wait_time)
        next_request = time.monotonic() + request_interval
        response=requests.post(url, data=payload, timeout=30)
        if response.status_code==200:
            cid=response.text.strip()
            print(f"SMILES {smiles} converted to CID {cid}")
            if cid.isdigit():
                sdf_url=f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/SDF?record_type=3d"
                wait_time = next_request - time.monotonic()
                if wait_time > 0:
                    time.sleep(wait_time)
                next_request = time.monotonic() + request_interval
                for attempt in range(3):
                    sdf_response=requests.get(sdf_url, timeout=30)
                    if sdf_response.status_code != 502 or attempt == 2:
                        break
                    time.sleep(1)
                if sdf_response.status_code==200:
                    sdf_path=outdir / f"{cid}.sdf"
                    with open(sdf_path, "wb") as f:
                        f.write(sdf_response.content)
                    print(f"Downloaded SDF for SMILES {smiles} (CID {cid})")
                else:
                    print(f"Failed to fetch SDF for CID {cid}. HTTP Status Code: {sdf_response.status_code}")
        else:
            print(f"Failed to convert SMILES {smiles} to CID. HTTP Status Code: {response.status_code}")
    print(f"Fetching complete. SDF files are saved in {outdir}")

def molfetch():
    choice=input("Fetch molecules by PubChem CIDs or SMILES? (Enter 1 for CIDs, 2 for SMILES) > ").strip()
    csvraw=selfile(title="Select CSV File")
    if csvraw.suffix.lower() == '.tsv':
        delimit = '\t'
    elif csvraw.suffix.lower() == '.csv':
        delimit = ','
    with open(csvraw, "r") as f:
        reader=csv.DictReader(f, delimiter=delimit)
        rows=list(reader)
        columns=[
            fieldname
            for fieldname in reader.fieldnames or []
            if any((row.get(fieldname) or "").strip() for row in rows)
        ]
        print("CSV Columns:", columns)
        while True:
            col=input("Enter the column name containing CIDs or SMILES > ").strip()
            if col in columns:
                break
            else:
                print(f"Column '{col}' not found in CSV. Please enter a valid column name.")
        vals=[row[col].strip() for row in rows if (row.get(col) or "").strip()]
    outdir,junk=seldir(title="Select Output Directory")
    if choice=="1":
        molfetch_cid(vals=vals,outdir=outdir)
    elif choice=="2":
        molfetch_smiles(vals=vals,outdir=outdir)
    else:
        print("Invalid choice. Please enter '1' or '2'.")
    return outdir
        
    