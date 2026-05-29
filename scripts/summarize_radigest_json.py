#!/usr/bin/env python3
import json
import sys
from pathlib import Path

print("\t".join([
    "file", "radigest_version", "enzymes", "min", "max",
    "fragments", "bases", "size_model",
    "weighted_fragments", "weighted_bases", "mean_weighted_length"
]))

for path in sys.argv[1:]:
    p = Path(path)
    with p.open() as fh:
        d = json.load(fh)

    ss = d.get("size_selection", {})
    print("\t".join(map(str, [
        p,
        d.get("radigest_version", ""),
        ",".join(d.get("enzymes", [])),
        d.get("min_length", ""),
        d.get("max_length", ""),
        d.get("total_fragments", ""),
        d.get("total_bases", ""),
        ss.get("model", ""),
        ss.get("weighted_fragments", ""),
        ss.get("weighted_bases", ""),
        ss.get("mean_weighted_length", "")
    ])))
