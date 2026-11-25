"""Extract comparable post-route metrics from one or more LibreLane runs."""
import argparse
import csv
import json
import sys
from pathlib import Path
from zipfile import ZipFile


def load_metrics(path):
    if path.suffix == ".zip":
        with ZipFile(path) as archive:
            matches = [n for n in archive.namelist() if n.endswith("/final/metrics.json")]
            if len(matches) != 1:
                raise ValueError(f"{path}: expected one final/metrics.json, found {len(matches)}")
            return json.loads(archive.read(matches[0]))
    return json.loads(path.read_text())


def summarize(metrics):
    result = {}
    for mode in ("setup", "hold"):
        key = f"timing__{mode}__ws"
        prefix = key + "__corner:"
        corners = {k[len(prefix):]: float(v) for k, v in metrics.items() if k.startswith(prefix)}
        if not corners:
            raise ValueError(f"No post-route {mode} corners")
        worst = min(corners.values())
        if abs(float(metrics[key]) - worst) > 1e-5:
            raise ValueError(f"Aggregate {mode} slack differs from the worst corner")
        result[f"{mode}_ws_ns"] = f"{worst:.6f}"
        result[f"{mode}_corner"] = "|".join(sorted(c for c, v in corners.items() if v == worst))
        result[f"{mode}_tns_ns"] = metrics[f"timing__{mode}__tns"]
    for label, key in {
        "stdcells": "design__instance__count__stdcell",
        "stdcell_area_um2": "design__instance__area__stdcell",
        "core_area_um2": "design__core__area",
        "slew_violations": "design__max_slew_violation__count",
        "fanout_violations": "design__max_fanout_violation__count",
        "cap_violations": "design__max_cap_violation__count",
        "route_drc_errors": "route__drc_errors",
        "magic_drc_errors": "magic__drc_error__count",
        "lvs_errors": "design__lvs_error__count",
    }.items():
        result[label] = metrics[key]
    result["stdcell_util_pct"] = f"{100 * metrics['design__instance__utilization__stdcell']:.4f}"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", metavar="LABEL=FILE", help="GDS_logs.zip or final metrics.json")
    args = parser.parse_args()
    writer = None
    for item in args.runs:
        label, sep, filename = item.partition("=")
        if not sep or not label or not filename:
            parser.error("Each run needs LABEL=FILE")
        try:
            row = {"run": label, **summarize(load_metrics(Path(filename)))}
        except (OSError, ValueError, KeyError) as error:
            parser.exit(1, f"{filename}: {error}\n")
        if writer is None:
            writer = csv.DictWriter(sys.stdout, fieldnames=row, lineterminator="\n")
            writer.writeheader()
        writer.writerow(row)


if __name__ == "__main__":
    main()
