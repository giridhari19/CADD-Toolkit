# CADD Toolkit: Technical Documentation

This document describes how the toolkit is implemented. It is a lightweight, interactive CLI layer that chains established tools (PubChem PUG REST, RDKit, Meeko, AutoDock Vina, PDB2PQR, PLIP) into a single workflow. It does not reimplement docking, scoring or interaction detection; each of those steps is delegated to the specialist tool.

---

## 1. Architecture and Workflow

### 1.1 Module overview

| Module | Role | External tools used |
|---|---|---|
| `main.py` | Interactive menu and workflow orchestration | `clear` (shell) |
| `molfetch.py` | Download 3D SDFs from PubChem (by CID or SMILES) | PubChem PUG REST (`requests`) |
| `molren.py` | Standardise SDF naming using PubChem synonyms | PubChem PUG REST, RDKit |
| `dockprep.py` | SDF to ligand PDBQT | RDKit, Meeko (Python API) |
| `protprep.py` | PDB to receptor PDBQT and Vina box | Meeko `mk_prepare_receptor.py` (subprocess) |
| `dock.py` | Batch Vina docking, ranking, SDF export | `vina`, Meeko `mk_export.py` (subprocesses), pandas |
| `analysis.py` | Docked poses to protonated complexes to PLIP reports | RDKit, Biopython, `pdb2pqr`, `plip` (subprocesses) |
| `pose0interaction.sh` | Collect pose-0 PLIP reports into one folder | bash |

### 1.2 How the modules interact

- **Filesystem-based hand-off.** Modules communicate through files and a few return values (`molfetch()` returns the output directory; `gen_prot()` returns the protein directory; `dock()` and `interaction()` accept an optional `dir`). There is no shared state or config file.
- **Interactive input.** Parameters are collected with `input()` prompts, and folders and files with Tkinter dialogs (`dock.seldir`, `dock.selfile`, and `filedialog` calls in `dockprep` and `protprep`).
- **Shared helpers.** `molfetch`, `molren` and `analysis` reuse `seldir`/`selfile` from `dock.py`.
- **Naming conventions as the interface between stages:**
  - The protein folder is named after the PDB ID and contains `<PDBID>.pdb` and `<PDBID>lig.sdf`.
  - Ligand files are named `<Name>_<CID>`, and `dock.py` and `analysis.py` recover the name and CID by splitting on `_`.
  - Ligand PDBQTs to be docked sit in a `ligands/` folder inside the protein folder.

---

## 2. Molecule Retrieval: [`molfetch.py`](../molfetch.py)

**Purpose.** Download 3D SDF records from PubChem for a list of compounds given in a table.

### Inputs

- A `.csv` or `.tsv` file chosen through a file dialog. The delimiter follows the extension (`.tsv` is tab, `.csv` is comma). Parsing uses `csv.DictReader`, so the file has a header row.
- Mode at a prompt: `1` for PubChem CIDs, `2` for SMILES.
- A column name at a prompt.
- An output directory chosen through a folder dialog.

### Column selection

The code lists the columns that contain at least one non-empty value and keeps asking until the user types one of them. Non-empty values in that column are stripped and used as the query list; blank cells are dropped.

### CID workflow (`molfetch_cid`)

For each CID, a GET request is sent to:

```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/SDF?record_type=3d
```

On HTTP 200 the response is written unmodified to `<outdir>/<cid>.sdf`.

### SMILES workflow (`molfetch_smiles`)

Two requests per compound:

1. `POST https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/cids/TXT` with form data `{"smiles": <smiles>}` resolves the SMILES to a CID.
2. If the response is an integer, the same 3D SDF GET is made for that CID and saved as `<outdir>/<cid>.sdf`.

### Rate limiting and retries

- Requests are scheduled at least 0.2 s apart (`request_interval = 1/5`), i.e. at most 5 requests per second, in line with PubChem's usage guideline.
- The SDF GET is attempted up to 3 times, retrying on HTTP 502 with a 1 s pause between attempts.
- All requests use a 30 s timeout.
- Any non-200 response is reported with its status code and the loop continues with the next compound.

### Output

SDFs are written directly into the chosen output directory, named by CID. `molfetch()` returns that directory to `main.py`, which can pass it straight to `molren` (Section 3).

---

## 3. SDF Molecule Renaming: [`molren.py`](../molren.py)

**Purpose.** Replace CID-only filenames with readable compound names while keeping the CID in the filename, so every later stage can recover both.

### Inputs

`molren(dir=None)`: a folder dialog is shown unless a directory is passed. `main.py` passes the fetch output directory directly when the user chooses to rename after fetching.

### Processing

1. Creates `<dir>/renamed/`.
2. Reads every top-level `*.sdf` in the folder with RDKit `SDMolSupplier`; every molecule in every file is processed individually.
3. **CID source:** the `PUBCHEM_COMPOUND_CID` property if present, otherwise the molecule's `_Name`. Molecules with neither are skipped with a warning.
4. Queries `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON`, using the same 0.2 s spacing and 502 retry pattern as `molfetch`.
5. Takes the first synonym returned, replaces any underscores in it with hyphens, sets it as the molecule's `_Name`, and writes the molecule to `renamed/<synonym>_CID_<cid>.sdf` with RDKit's `SDWriter`.
6. If the synonym lookup fails, the molecule is still written as `renamed/UnknownName_CID_<cid>.sdf` with `_Name` set to the CID.

### Why this matters downstream

Reserving `_` as the field separator is what lets later modules parse filenames reliably: `dockprep.py` builds `<Name>_<CID>.pdbqt`, `dock.py` reads name and CID from the first two `_`-separated fields, and `analysis.py` uses the same fields to build per-ligand report folders. A single consistent naming scheme therefore carries identity from PubChem through to the final interaction reports.

### Output

One SDF per molecule in `<dir>/renamed/`; the original files are left untouched.

---

## 4. Ligand Preparation: [`dockprep.py`](../dockprep.py)

**Purpose.** Convert 3D ligand SDFs into PDBQT files for Vina.

### Inputs (prompts)

| Prompt | Behaviour |
|---|---|
| Batch prep multiple SDFs? | Non-blank: select a folder and process its top-level `*.sdf` files. Blank: select a single SDF. |
| Select output directory? | Non-blank: choose a folder (intended to be the protein folder's `ligands/`). Blank: auto-generate. |

Auto-generated output folder: for a single file, `<sdf parent>/<sdf stem>/`; in batch mode, `<selected folder>/ligands/`.

### Processing (`prep_mol`)

```python
mol = Chem.AddHs(mol, addCoords=True)
setup = MoleculePreparation().prepare(mol)[0]
pdbqt, ok, err = PDBQTWriterLegacy.write_string(setup)
```

- RDKit adds explicit hydrogens with coordinates; the input 3D geometry is otherwise used as given.
- Meeko's `MoleculePreparation` is used with default settings.
- The CID is read from `PUBCHEM_COMPOUND_CID`. The name is the first whitespace-delimited token of `_Name`.

### Output and reporting

`<out_dir>/<name>_<cid>.pdbqt`. Meeko's success flag is checked for each molecule; failures are printed with Meeko's message, and a final summary reports the number processed, succeeded and failed.

---

## 5. Protein Preparation: [`protprep.py`](../protprep.py)

**Purpose.** Produce a Vina-ready receptor and docking box by wrapping Meeko's `mk_prepare_receptor.py`.

### Inputs

The user selects a protein folder by dialog; its name is used as the PDB ID. The folder is expected to contain:

- `<PDBID>.pdb`: the protein structure
- `<PDBID>lig.sdf`: the co-crystallised ligand, used to define the box

Prompts: box padding, an optional default altloc, and an optional list of wanted altlocs.

### Command construction

```python
payload = ["mk_prepare_receptor.py",
           "--read_pdb", f"{protid}.pdb",
           "-o", protid,
           "-p", "-v",
           "--box_enveloping", f"{protid}lig.sdf",
           "--padding", pad]
# added only if provided:
#   "--default_altloc", <value>
#   "--wanted_altloc",  <value>
subprocess.run(payload, cwd=protdir, capture_output=True, text=True)
```

Receptor parsing, atom typing and PDBQT writing are all done by Meeko; this module builds the command and manages the altloc dialogue. `-p` and `-v` request the PDBQT and the Vina box file, giving `<PDBID>.pdbqt` and `<PDBID>.box.txt`, which `dock.py` consumes.

### Docking box

`--box_enveloping` builds the box around the co-crystallised ligand SDF plus the user's padding (the prompt recommends 5). The box therefore reflects the experimentally observed binding site.

### Alternate-location handling

Alternate conformations are resolved by the user through a two-stage mechanism:

1. **Up-front choice (optional).** The prompt shows the format for `--wanted_altloc` (`CHAIN:INDEX1,INDEX2,...=altloc1,CHAIN1...=altloc2,...`). A *default* altloc applies broadly, and *wanted* altlocs override it for specific residues.
2. **Guided retry on failure.** The first run's output is printed. If the return code is non-zero and Meeko's output contains "alternate location", the module explains how to choose: inspect the PDB file, use the altloc with the highest occupancy for most residues as the default, and list the exceptions as wanted altlocs. It then re-prompts for both values, appends them to the command, and re-runs Meeko with output streaming directly to the terminal.

This keeps the structural decision with the researcher while still handling the common failure mode of residues that carry several altlocs.

### Output

`<PDBID>.pdbqt` and `<PDBID>.box.txt` in the protein folder; the function returns the folder path.

---

## 6. Molecular Docking: [`dock.py`](../dock.py)

**Purpose.** Run AutoDock Vina over a folder of ligands, rank the results, shortlist by score, and export the docked poses to SDF.

### Protein directory

`dock(dir=None)` shows a folder dialog unless a directory is passed. In the protein-preparation path of `main.py`, the folder returned by `gen_prot()` is passed in directly. The PDB ID is again the folder name.

### Parameters (prompts)

| Prompt | Vina option | If left blank |
|---|---|---|
| Exhaustiveness | `--exhaustiveness` | Vina default (8) |
| Num modes | `--num_modes` | Vina default (9) |
| Energy range | `--energy_range` | Vina default (3) |
| Seed | `--seed` | random seed |

A user-defined seed lets a docking run be repeated with the same inputs and parameters.

### Vina invocation

```python
["vina",
 "--receptor", f"{protid}.pdbqt",
 "--config",   f"{protid}.box.txt",
 "--batch",    "ligands",
 "--dir",      "docked",
 "--verbosity", "2",
 # + optional --exhaustiveness / --num_modes / --energy_range / --seed
]
# executed with cwd=protdir
```

- All paths are relative to the protein folder (`cwd=protdir`).
- The box centre and size come from the config file written during protein preparation.
- Vina's `--batch` option docks every PDBQT in the given directory (`ligands/`) in a single call, and writes the results to `docked/`.
- Because the batch is simply the contents of `ligands/`, the co-crystallised ligand (prepared with `dockprep.py` from `<PDBID>lig.sdf`) can be docked alongside the test compounds as a redocking control.

### Live output and logging

Vina runs under `subprocess.Popen` with stderr merged into stdout. The output is read one character at a time and echoed to the terminal while being written to `<protdir>/docking.log`, so progress output that is not newline-terminated appears live. The log is rewritten on each run.

### Result parsing

For each `docked/*.pdbqt`, the file stem gives the name and CID. All `REMARK VINA RESULT:` lines are read; the lowest affinity is taken as the best score and its position in the file as the pose number. Results go into a pandas DataFrame (`Name`, `CID`, `Affinity`, `Pose`), sorted by affinity and printed.

### Shortlisting

The user enters an energy difference; ligands within that range of the best score are retained.

| File (in `docked/`) | Contents |
|---|---|
| `<PDBID>_results.csv` | All ligands: Name, CID, Affinity, Pose |
| `<PDBID>_useful.csv` | Shortlist within the chosen energy difference: Name, CID, Affinity |

### SDF export

```python
subprocess.run(["mk_export.py", *qts, "--suffix", "_docked"], cwd=sdff, check=True)
```

All docked PDBQTs are converted to multi-pose SDFs in `docked/sdf files/` using Meeko, ready for the analysis stage.

---

## 7. Interaction Report Generation: [`analysis.py`](../analysis.py)

### Purpose and scope

This module produces **standardised interaction reports** for docked poses so they can be reviewed consistently. It does not judge whether an interaction is biologically meaningful and does not filter or score the PLIP output. Biological and structural interpretation remains with the researcher.

### Pipeline

Entry point: `interaction(dir=None)`, which calls `merge_pdb()`, which calls `sdf_to_pdb()`. The protein folder comes from a dialog or from the `dir` argument (passed by `main.py` in the automatic path).

#### Step 1: SDF to PDB (`sdf_to_pdb`)

- Pose discovery: every `docked/sdf files/*.sdf`.
- Each SDF is read with RDKit and the **first two poses (indices 0 and 1)** are written as `docked/pdb files/<Name>_<CID>_pose_<i>.pdb`. Pose indices are 0-based, whereas the `Pose` column in `_results.csv` is 1-based.

#### Step 2: Receptor protonation with PDB2PQR

```
pdb2pqr --ff=AMBER [--titration-state-method=propka --with-ph=<pH>] \
        <PDBID>.pdb <PDBID>.pqr --pdb-output <PDBID>_h.pdb
```

- The user is prompted for a pH. If provided, it is passed to PDB2PQR as `--with-ph` together with `--titration-state-method=propka`. If left blank, PDB2PQR is run without a titration-state method.
- The command runs in the protein folder with `check=True`; the intermediate `.pqr` is then deleted.
- Output: `<PDBID>_h.pdb`, the protein with hydrogens added.

**Why this step is separate from docking.** Docking uses the Meeko-prepared receptor and does not need explicit hydrogens. Interaction analysis does: hydrogen-bond and related interactions are assigned using hydrogen positions. The hydrogenated receptor is therefore generated only for the analysis stage, by a fixed, scripted call (AMBER force field, optional PROPKA at a user-chosen pH) rather than left to whichever analysis tool is used later. For a given input structure and settings, PDB2PQR is expected to return the same result, so every pose is analysed against the same hydrogenated protein.

#### Step 3: Complex generation (`merge_pdb`)

For each ligand pose, the hydrogenated protein is parsed with Biopython, the ligand's chain is renamed **`Z`** and added to model 0, and the result is saved as `docked/complexes/<Name>_<CID>_pose_<i>_complex.pdb`. A dedicated chain keeps the ligand distinct from the protein chains.

#### Step 4: PLIP

For each complex, a folder `interactions/<Name>_<CID>/pose <i>/` is created and PLIP is run inside it:

```
plip -f <complex.pdb> --nohydro -xtp
```

`-x`, `-t` and `-p` request XML, text and PyMOL outputs. `--nohydro` tells PLIP not to add its own hydrogens, so the hydrogens supplied by PDB2PQR (protein) and by the docked SDF (ligand) are the ones used.

#### Step 5: Collecting pose-0 reports

`pose0interaction.sh` (stored next to `analysis.py`) is run from `interactions/`. For each ligand folder it copies the pose-0 XML and TXT reports into `interactions/pose0 files/` as `<Name>_<CID>_pose0_report.xml` and `.txt`. `<PDBID>_useful.csv` is copied into the same folder, so the shortlist and its reports are together in one place. The plain-text PLIP reports are readable as they are and are intended for direct review.

### Using PLIP and BIOVIA Discovery Studio together

PLIP is the automated component: it produces reports for every ligand in one pass. BIOVIA Discovery Studio is not called by the toolkit; the intended pattern is that the researcher opens selected, promising ligands in it manually, for example to produce documentation figures. Because the hydrogenated receptor (`<PDBID>_h.pdb`) and the complex PDBs are fixed files on disk, both tools can work from identical structures with identical hydrogen placement, which removes one source of difference between them. The two programs use their own interaction criteria, so this makes their results more comparable but does not guarantee they will be identical.

---

## 8. Main CLI: [`main.py`](../main.py)

### Menu

```
1. Fetch Molecules from PubChem     → molfetch.molfetch()  [+ optional molren.molren(dir=outdir)]
2. SDF Molecule Renaming            → molren.molren()
3. Ligand Preparation               → dockprep.gen_lig_qt()
4. Protein Preparation              → protprep.gen_prot() [+ optional dock + optional analysis]
5. Docking                          → dock.dock()
6. Analysis                         → analysis.interaction()
7. Exit
```

The screen is cleared each time the menu is shown.

### Dispatch and return behaviour

Each choice calls the corresponding module and then `end()`, which prompts: Enter returns to the menu, `1` exits. Choice 7 exits immediately.

### Sequential workflows

- **Fetch to rename.** After option 1, the user is asked whether to rename the fetched molecules (`1` for yes); the fetch directory is passed straight to `molren`.
- **Protein preparation to docking to interaction reporting.** Option 4 asks how many proteins to prepare and loops over them. For each protein, `gen_prot()` returns the protein folder; the user is asked whether to dock; if so, `dock.dock(dir=protdir)` runs on that folder, and the user is then asked whether to run `analysis.interaction(dir=protdir)`. The folder is passed along at each step, so the user is not asked to reselect it, and several proteins can be taken through preparation, docking and analysis in one session.
- Each stage keeps its own parameter prompts (padding and altlocs, Vina parameters, pH, and so on).

---

## 9. File and Directory Organisation

Representative layout for one protein:

```
<PDBID>/                          # folder name = PDB ID
├── <PDBID>.pdb                   # user-provided
├── <PDBID>lig.sdf                # user-provided reference ligand
├── <PDBID>.pdbqt                 # protprep (Meeko)
├── <PDBID>.box.txt               # protprep (Meeko)
├── <PDBID>_h.pdb                 # analysis (PDB2PQR output)
├── ligands/                      # <Name>_<CID>.pdbqt (dockprep)
├── docking.log                   # dock (full Vina console output)
├── docked/
│   ├── *.pdbqt                   # Vina output, one file per ligand
│   ├── <PDBID>_results.csv
│   ├── <PDBID>_useful.csv
│   ├── sdf files/                # mk_export.py output (suffix _docked)
│   ├── pdb files/                # <Name>_<CID>_pose_0.pdb, _pose_1.pdb
│   └── complexes/                # <Name>_<CID>_pose_<i>_complex.pdb
└── interactions/
   ├── <Name>_<CID>/
    │   ├── pose 0/               # PLIP XML, TXT, PyMOL outputs
    │   └── pose 1/
    └── pose0 files/              # <Name>_<CID>_pose0_report.{xml,txt}, └──   
        └──<PDBID>_useful.csv
```

Ligand side, before `ligands/` is placed in the protein folder:
`<fetch dir>/<CID>.sdf` → `<fetch dir>/renamed/<Synonym>_CID_<CID>.sdf` → `<renamed dir>/ligands/<Name>_<CID>.pdbqt`.

---

