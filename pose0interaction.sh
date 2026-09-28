#!/bin/bash
mkdir -p "./pose0 files"
for mol in ./*/; do
    [ "$mol" = "./pose0 files/" ] && continue

    mol_name=$(basename "$mol")
    pose0="${mol}pose 0"

    if [ -d "$pose0" ]; then
        for xml in "$pose0"/*.xml; do
            [ -f "$xml" ] || continue

            cp "$xml" "./pose0 files/${mol_name}_pose0_report.xml"

            echo "Copied: $xml → ./pose0 files/${mol_name}_pose0_report.xml"
        done
        for txt in "$pose0"/*.txt; do
            [ -f "$txt" ] || continue

            cp "$txt" "./pose0 files/${mol_name}_pose0_report.txt"

            echo "Copied: $txt → ./pose0 files/${mol_name}_pose0_report.txt"
        done
    fi
done
echo "Done."