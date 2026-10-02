# CADD Pipeline
### *A modular command-line toolkit for automating repetitive ligand retrieval, molecular preparation, molecular docking, and post-docking interaction report generation.*

![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Linux](https://img.shields.io/badge/Platform-Linux-E95420?logo=linux&logoColor=white)
![RDKit](https://img.shields.io/badge/RDKit-Cheminformatics-1f77b4)
![Meeko](https://img.shields.io/badge/Meeko-Docking%20Preparation-6f42c1)
![AutoDock Vina](https://img.shields.io/badge/AutoDock%20Vina-Docking-2ea44d)
![PLIP](https://img.shields.io/badge/PLIP-Interaction%20Analysis-teal)

## Table of Contents

* [Project Motivation](#project-motivation)
* [Project Objective](#project-objective)
* [Workflow](#workflow)
* [Features](#features)
* [Key Design Decisions](#key-design-decisions)
* [Example Usage](#example-usage)

  * [Example Directory](#example-directory)
  * [Initialization](#initialization)
  * [1. Retrieve and Rename Ligands](#1-retrieve-and-rename-ligands)
  * [2. Prepare the Ligands](#2-prepare-the-ligands)
  * [3. Prepare the Protein](#3-prepare-the-protein)
  * [4. Perform Molecular Docking](#4-perform-molecular-docking)
  * [5. Generate Interaction Reports](#5-generate-interaction-reports)
  * [Complete Workflow](#complete-workflow)
* [Reproducibility Considerations](#reproducibility-considerations)
* [Error Handling](#error-handling)
* [Technical Limitations](#technical-limitations)
* [Future Development](#future-development)

---
## Project Motivation

CADD workflows often involve repetitive use of command-line tools and Python functions for different stages of the workflow.

* **Repetitive operations:** Ligand retrieval, preparation, receptor preparation, docking, and post-docking processing involve repeated commands and file operations.
* **Multiple file formats:** The workflow requires several file conversions and molecular preparation steps between different tools.
* **Tool fragmentation:** Individual CADD tools have their own interfaces, commands, and file-format requirements, making it cumbersome to move between them.
* **Batch processing:** Performing these steps manually becomes increasingly difficult when working with large libraries of ligands or multiple protein targets.
* **Human error:** Repeated manual file handling and command execution can introduce errors, particularly during large-scale processing.

## Project Objective

Develop a lightweight CLI-based CADD toolkit to:

* Automate ligand retrieval, preparation, and batch docking.
* Standardise molecular identification and file naming as `SYNONYM_CID`.
* Integrate established CADD tools into a consistent workflow.
* Improve reproducibility of docking through user-defined random seeds.
* Improve reproducibility of protein–ligand interaction analysis through deterministic protein protonation using PDB2PQR with user-defined pH.
* Simplify batch processing while retaining human interpretation of docking and interaction results.

## Workflow

|Workflow|External Tool(s) Used|
|---| ---|
|Molecule Retrieval|PubChem PUG REST API|
|SDF Renaming|PubChem PUG REST API|
|Ligand Preparation|RDKit, Meeko|
|Protein Preparation|Meeko|
|Molecular Docking|AutoDock Vina|
|Interaction Report|PDB2PQR, PLIP, BIOVIA Discovery Studio|

## Features

* **PubChem Molecule Retrieval** — Retrieve compounds from CID or SMILES lists provided through CSV/TSV files.
* **Standardised Molecular Naming** — Rename compounds using PubChem synonyms with consistent `NAME_CID` naming.
* **Batch Ligand Preparation** — Prepare multiple ligands for docking using RDKit and Meeko.
* **Protein Preparation** — Prepare receptors and generate docking-box configurations for AutoDock Vina.
* **Batch Molecular Docking** — Run ligand libraries through AutoDock Vina with configurable parameters and user-defined random seeds.
* **Interaction Reporting** — Generate organised PLIP interaction reports using consistently protonated protein structures.
* **Reproducible Workflow** — Standardised naming, deterministic PDB2PQR protonation, configurable pH, and user-defined docking seeds improve workflow reproducibility.
* **Modular CLI** — Use individual workflow stages independently or chain multiple stages together through a single command-line interface.

For detailed implementation and technical information, see the **[Technical Documentation](./docs/Technical%20Details.md)**.

## Key Design Decisions

* **Modular architecture:** Each workflow stage is implemented as an independent Python module, allowing individual tools to be used or combined into a larger workflow.
* **CLI-based interface:** A lightweight command-line interface was chosen to keep the toolkit simple and suitable for batch processing.
* **Established tool integration:** Existing, validated CADD and cheminformatics tools are integrated rather than recreating their functionality.
* **Standardised file organisation:** Consistent naming and dedicated output directories make large docking workflows easier to track and reproduce.
* **Reproducible docking:** User-defined random seeds allow docking runs to be repeated under the same conditions.
* **Consistent interaction analysis:** PDB2PQR provides a deterministic, pH-controlled hydrogenated protein structure as a common input for PLIP and BIOVIA Discovery Studio.
* **Human-led interpretation:** The toolkit automates preparation and reporting while leaving biological interpretation of interactions to the researcher.

## Example Usage

A complete example workflow is provided in the [`example/`](./example/) directory. It demonstrates ligand retrieval, preparation, protein preparation, docking, redocking validation, and interaction reporting using the **6EQM** structure.

### Example Directory

```text
example/
├── raw ligands/
│   └── ligands.csv
│
└── 6EQM/
    ├── 6EQM.pdb
    └── 6EQMlig.sdf
```

### Initialization:
>**Ensure you are either using Linux or WSL for the entire workflow.**     

First clone this repo using
```bash
git clone https://github.com/giridhari19/CADD-Toolkit.git)
```
Then setup the Environment using micromamba
```bash
cd CADD-Toolkit
micromamba env create -f environment.yml
micromamba activate dock
```
This should download all the necessary libraries and scripts.
### 1. Retrieve and Rename Ligands

Run the toolkit:

```bash
python main.py
```
This opens the main selection menu:     
![main menu](./docs/main%20menu.png)

Select:

```text
1. Fetch Molecules from PubChem
```

Choose **CID** as the input type and select:

```text
example/raw ligands/ligands.csv
```

Select the column containing the CIDs and specify the `6EQM` directory as the output location.

After retrieval, select **1** when prompted to automatically proceed with molecule renaming.

The retrieved compounds are renamed using their PubChem synonyms and CID:

```text
NAME_CID.sdf
```

The output directory for these renamed ligands select the 6EQM folder

---

### 2. Prepare the Ligands

Select:

```text
3. Ligand Preparation
```

Choose **batch processing** and select the `6EQM` directory containing the renamed SDF files.

Select automatic output-directory generation.

The toolkit prepares the ligands using RDKit and Meeko and generates:

```text
6EQM/
└── ligands/
    ├── NAME_CID.pdbqt
    ├── NAME_CID.pdbqt
    └── ...
```

---

### 3. Prepare the Protein

Select:

```text
4. Protein Preparation
```

Select the `6EQM` directory.

Enter the necessary amount of padding.

For the alternate-location option, enter:

```text
A
```
> Note: This alternate location is necessary for this 6EQM.pdb specifically. This may or may not be needed if a different pdb is used

The prepared receptor and docking-box files are generated in the `6EQM` directory:

```text
6EQM/
├── 6EQM.pdb
├── 6EQM.pdbqt
├── 6EQM.box.pdb
└── 6EQM.box.txt
```

The `.box.txt` file is subsequently used as the AutoDock Vina configuration file.

When prompted whether to dock the prepared protein, select **1**.

---

### 4. Perform Molecular Docking

The docking workflow automatically continues using the same `6EQM` directory.

The following Vina parameters can be specified:

* Exhaustiveness
* Energy range
* Number of modes
* Random seed

All are optional and can be left blank to use the configured defaults.
> The example [`docked example`](./docked%20example/) used seed value as `320`

The ligand library is then batch-docked against the prepared receptor. Wait until the docking is completed.

Because `6EQMlig.sdf` is also present in the directory, the toolkit additionally performs **redocking RMSD analysis using `obrms`** to assess the reproduced reference-ligand pose.

The docking results and calculated binding energies are then displayed and output to `6EQM_results.csv`

The toolkit subsequently prompts for an energy-difference threshold to identify compounds for inclusion in `6EQM_useful.csv` 
This file conatins information of ligands with energy difference specified previously from the highest negative binding energy.

Completed docking: 
![dock results](./docs/dock%20result.png)

---

### 5. Generate Interaction Reports

After docking, select **1** when prompted to continue to analysis.

The interaction-analysis workflow asks for a pH value for protein protonation. (optional)
> The example [`docked example`](./docked%20example/) used pH of `7.4`

PDB2PQR is then used to generate the hydrogenated/protonated protein structure, which is used for subsequent interaction analysis.

PLIP is used to generate the protein–ligand interaction reports.

The resulting reports are organised in:

```text
6EQM/
└── interactions/
    └── ...
```

The `interactions/` directory can then be explored to inspect the detected protein–ligand interactions for the docked poses.

Detailed interaction interpretation is intentionally left to the researcher rather than being automatically classified by the toolkit.

---

### Complete Workflow

```text
ligands.csv
     │
     ▼
PubChem retrieval
     │
     ▼
SDF renaming
     │
     ▼
Ligand preparation
     │
     ▼
Protein preparation
     │
     ▼
AutoDock Vina docking
     │
     ├── Reference-ligand redocking RMSD
     │
     ├── Binding-energy filtering
     │
     └── useful.csv
     │
     ▼
PDB2PQR protonation
     │
     ▼
PLIP interaction reports
     │
     ▼
Manual structural interpretation
```

> **Note:** This example demonstrates the intended end-to-end workflow. Individual toolkit modules can also be run independently from the main menu.

## Reproducibility Considerations

- **Standardised compound naming.** `<Synonym>_CID_<CID>.sdf` becomes `<Name>_<CID>.pdbqt`, tying every downstream file to a PubChem CID.
- **Scripted receptor protonation.** PDB2PQR with a fixed force field (AMBER) and an optional user-defined pH (PROPKA), producing a single `_h.pdb` used for every pose.
- **Identical hydrogens for all PLIP runs** (`--nohydro` with a shared hydrogenated receptor).
- **User-defined Vina random seed**, together with explicit exhaustiveness, number of modes and energy range.
- **Consistent output organisation** (Section 9), with one report per ligand and pose and a collected `pose0 files/` folder.
- **Logging.** The complete Vina console output is saved to `docking.log`.
- **Controlled PubChem access** through rate limiting and retries.
- **Environment definition** in `environment.yml` (conda-forge).

---

## Error Handling

The following checks are implemented in the code.

| Module | Handling |
|---|---|
| `main.py` | Invalid menu choices are reported and return to the menu. |
| `molfetch.py` | Column name is validated against the file's non-empty columns, with re-prompting. Blank cells are dropped. HTTP status of each request is checked and non-200 responses are reported per compound. 502 responses are retried (3 attempts, 1 s pause). 30 s request timeout. SMILES-to-CID results are checked to be numeric before fetching. |
| `molren.py` | Unreadable molecules are skipped. Molecules with no CID or name are skipped with a warning. 502 responses are retried. A failed synonym lookup falls back to `UnknownName_CID_<cid>.sdf`, so the molecule is not lost. An empty synonym is detected and skipped. |
| `dockprep.py` | Unreadable molecules are counted as failures. Meeko's success flag is checked and its message printed on failure. Processed, succeeded and failed counts are reported. |
| `protprep.py` | Altloc failures are detected from the exit code and Meeko output, followed by a guided retry (Section 5). |
| `dock.py` | Blank prompts fall back to Vina defaults. Files not following the `<Name>_<CID>` pattern are ignored when parsing results. `mk_export.py` runs with `check=True`. |
| `analysis.py` | Unreadable poses are reported and skipped. `pdb2pqr` and the cleanup command run with `check=True`. The PLIP return code is checked per complex. The shell script only copies reports that exist. |

---

## Technical Limitations

**Platform and interface**
- The toolkit uses `clear`, `rm`, `cp` and `bash`, and Tkinter dialogs, so it requires a Unix-like environment with a display.
- It is interactive only; there are no command-line arguments or configuration file, which limits unattended or scripted runs.

**Scope of the underlying methods**
- The docking box can only be defined from a co-crystallised ligand SDF.
- The receptor is treated as rigid; no flexible-residue options are passed to Meeko or Vina.
- Ligands receive explicit hydrogens but no pH-dependent protonation or tautomer handling.
- Only the first two poses (indices 0 and 1) are converted and analysed; only pose 0 reports are collected into `pose0 files/`.
- Interaction analysis runs on every docked ligand, not only the energy-based shortlist. (Delibrate as energy scores are not an indicator of good interaction)
- Reports are generated but not interpreted or ranked; this is deliberate but means review is manual.

**Conventions and inputs**
- The protein folder must be named after the PDB ID, and `ligands/` must be placed inside it manually (or selected as the output folder in `dockprep`).
- Filenames are parsed by splitting on `_`, so a compound name containing `_` (for example if `molren.py` is bypassed) breaks parsing in `dock.py` and `analysis.py`. Other characters that are unsafe in filenames are not sanitised in synonyms.
- Numeric prompts (padding, Vina parameters, pH, energy difference) are not validated.
- The fetch mode (CID or SMILES) is checked only after the file, column and output folder have been chosen, and an unsupported table extension (other than `.csv` or `.tsv`) is not handled.
- SMILES queries that resolve to anything other than a single CID are skipped.
- The ligand chain is renamed to `Z` in complexes; a protein that already has chain `Z` would conflict.

**Error handling and robustness**
- The Vina exit code is not checked, and an empty docking result set is not handled.
- Only altloc-related Meeko failures have a dedicated recovery path.
- Cancelled file dialogs are not handled.
- There are no automated tests.

**Provenance and environment**
- The values entered at prompts (pH, seed, padding, altloc choices, Vina parameters) and the exact command lines are not written to a file; only the Vina console output is logged.
- `environment.yml` does not pin versions, and `pandas` and `requests` are not listed explicitly, though both are imported.

---

## Future Development

These are possible extensions that follow naturally from the current design. None are implemented.

- Write a run manifest (JSON or YAML) recording prompt answers, command lines and tool versions.
- Add command-line arguments alongside the prompts for non-interactive use, and replace shell calls (`rm`, `cp`, `bash`) with `pathlib` and `shutil` for portability.
- Make the number of analysed poses configurable, and optionally restrict analysis to the shortlist in `_useful.csv`.
- Sanitise compound names more broadly and validate numeric inputs.
- Broaden error handling for network failures and subprocess exit codes.
- Pin tool versions in `environment.yml`.