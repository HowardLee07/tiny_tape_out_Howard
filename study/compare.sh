#!/bin/sh
set -eu
export LC_ALL=C
: "${1:?usage: study/compare.sh /absolute/path/to/sky130_fd_sc_hd__tt_025C_1v80.lib}"
root=$(git rev-parse --show-toplevel)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp "$1" "$work/hd.lib"
cd "$root"
git show f3f16c4:src/logic_analyzer_4ch.v > "$work/baseline.v"
cp src/logic_analyzer_4ch.v "$work/candidate.v"
cp src/project.v study/equivalence.ys "$work/"
cd "$work"
yosys -Q -s equivalence.ys > proof.log
grep -E 'are proven|Equivalence successfully proven' proof.log
for variant in baseline candidate; do
    mkdir -p "$variant/src"
    cp "$variant.v" "$variant/src/logic_analyzer_4ch.v"
    cp project.v "$variant/src/"
    (
        cd "$variant"
        yosys -Q -p 'read_verilog src/*.v; synth -flatten -noabc -top tt_um_howardlee_logic_analyzer_4ch; dfflibmap -liberty ../hd.lib; abc -liberty ../hd.lib; clean; stat -liberty ../hd.lib; write_json mapped.json' > mapping.log
        python3 - "$variant" <<'PY'
import json
import sys
from pathlib import Path

design = json.loads(Path("mapped.json").read_text())
top = design["modules"]["tt_um_howardlee_logic_analyzer_4ch"]
cells = [cell["type"] for cell in top["cells"].values() if cell["type"] != "$scopeinfo"]
if any(not cell.startswith("sky130_fd_sc_hd__") for cell in cells):
    sys.exit("Unexpected unmapped cells")
print(f"{sys.argv[1]}: {len(cells)} mapped SKY130 cells")
PY
        grep 'Chip area for module' mapping.log
    )
done
