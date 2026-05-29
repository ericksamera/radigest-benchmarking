#!/usr/bin/env python3
import re
import sys
from pathlib import Path

patterns = {
    "elapsed": re.compile(r"Elapsed \\(wall clock\\) time.*: (.+)"),
    "user_time_s": re.compile(r"User time \\(seconds\\): (.+)"),
    "system_time_s": re.compile(r"System time \\(seconds\\): (.+)"),
    "max_rss_kb": re.compile(r"Maximum resident set size \\(kbytes\\): (.+)")
}

print("file\telapsed\tuser_time_s\tsystem_time_s\tmax_rss_kb")

for path in sys.argv[1:]:
    p = Path(path)
    vals = {k: "" for k in patterns}
    txt = p.read_text(errors="replace")
    for key, pat in patterns.items():
        m = pat.search(txt)
        if m:
            vals[key] = m.group(1)
    print(f"{p}\t{vals['elapsed']}\t{vals['user_time_s']}\t{vals['system_time_s']}\t{vals['max_rss_kb']}")
