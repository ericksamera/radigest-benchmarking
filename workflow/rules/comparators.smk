# Comparator interval-equivalence rules for Stage 4.
# These rules are registry-driven from config/comparators.tsv and
# config/comparator_cases.tsv. They port only exact interval comparators:
# Digital_RADs.py and DDRADSEQTOOLS rsitesearch.py.

import csv
from pathlib import Path

COMPARATOR_CASE_MANIFEST = "config/comparator_cases.tsv"
COMPARATOR_REGISTRY = "config/comparators.tsv"
COMPARATOR_CUT_EQUIVALENCE_SUMMARY = "results/comparators/cut_equivalence_summary.tsv"
COMPARATOR_INTERVAL_TABLE = "results/manuscript/tables/table_03_interval_comparisons.tsv"


def _read_rows(path):
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = [
            row
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


COMPARATOR_CASE_ROWS = _read_rows(COMPARATOR_CASE_MANIFEST)
COMPARATOR_CASE_BY_ID = {row["case_id"]: row for row in COMPARATOR_CASE_ROWS}
COMPARATOR_ROWS = _read_rows(COMPARATOR_REGISTRY)
COMPARATOR_BY_TOOL = {row["tool_id"]: row for row in COMPARATOR_ROWS}
CONDITION_ROWS_FOR_COMPARATORS = _read_rows("config/conditions.tsv")
CONDITION_BY_ID_FOR_COMPARATORS = {
    row["condition_id"]: row for row in CONDITION_ROWS_FOR_COMPARATORS
}

DIGITAL_RADS_CASES = [
    row["case_id"]
    for row in COMPARATOR_CASE_ROWS
    if row["tool_id"] == "digital_rads"
    and row.get("required_for_nonempirical", "false").lower() == "true"
]
DDRADSEQTOOLS_CASES = [
    row["case_id"]
    for row in COMPARATOR_CASE_ROWS
    if row["tool_id"] == "ddradseqtools"
    and row.get("required_for_nonempirical", "false").lower() == "true"
]

DIGITAL_RADS_SUMMARIES = [
    f"results/comparators/digital_rads/{case_id}.summary.tsv"
    for case_id in DIGITAL_RADS_CASES
]
DDRADSEQTOOLS_SUMMARIES = [
    f"results/comparators/ddradseqtools/{case_id}.interval_compare.summary.tsv"
    for case_id in DDRADSEQTOOLS_CASES
]
COMPARATOR_INTERVAL_OUTPUTS = DIGITAL_RADS_SUMMARIES + DDRADSEQTOOLS_SUMMARIES
COMPARATOR_ALL_OUTPUTS = COMPARATOR_INTERVAL_OUTPUTS + [
    COMPARATOR_CUT_EQUIVALENCE_SUMMARY,
    COMPARATOR_INTERVAL_TABLE,
]


def comparator_case(case_id):
    try:
        return COMPARATOR_CASE_BY_ID[case_id]
    except KeyError as exc:
        raise ValueError(f"unknown comparator case_id: {case_id}") from exc


def condition_for_case(case_id):
    row = comparator_case(case_id)
    condition_id = row["condition_id"]
    try:
        return CONDITION_BY_ID_FOR_COMPARATORS[condition_id]
    except KeyError as exc:
        raise ValueError(
            f"case {case_id} references unknown condition_id: {condition_id}"
        ) from exc


def comparator_required_path(tool_id):
    try:
        value = COMPARATOR_BY_TOOL[tool_id]["required_paths"]
    except KeyError as exc:
        raise ValueError(f"unknown comparator tool_id: {tool_id}") from exc
    paths = [part.strip() for part in value.split(";") if part.strip()]
    if not paths or paths == ["NA"]:
        raise ValueError(f"comparator {tool_id} has no executable required_paths")
    return paths[0]


def case_reference(wc):
    return comparator_case(wc.case_id)["reference_path"]


def case_condition_id(wc):
    return comparator_case(wc.case_id)["condition_id"]


def case_enzyme1(wc):
    return condition_for_case(wc.case_id)["enzyme_1"]


def case_enzyme2(wc):
    return condition_for_case(wc.case_id)["enzyme_2"]


def case_enzymes_csv(wc):
    condition = condition_for_case(wc.case_id)
    enzyme2 = condition["enzyme_2"]
    if enzyme2 in {"", "NA", "none", "None"}:
        return condition["enzyme_1"]
    return f"{condition['enzyme_1']},{enzyme2}"


def case_min_size(wc):
    return int(condition_for_case(wc.case_id)["min_size"])


def case_max_size(wc):
    return int(condition_for_case(wc.case_id)["max_size"])


def ddradseqtools_tool_max_size(wc):
    # rsitesearch.py filters on its own fragment representation. Run a slightly
    # wider upper bound, then enforce the exact cut-to-cut window in the
    # normalizer so valid radigest intervals are not lost before normalization.
    return case_max_size(wc) + 4


def ddradseqtools_repo(_wc):
    rsitesearch = Path(comparator_required_path("ddradseqtools"))
    return str(rsitesearch.parents[1])


rule comparators_all:
    input:
        COMPARATOR_ALL_OUTPUTS


rule radigest_for_digital_rads:
    input:
        ref=case_reference
    output:
        json="results/comparators/digital_rads/raw/{case_id}.radigest.json",
        tsv="results/comparators/digital_rads/raw/{case_id}.radigest.fragments.tsv"
    log:
        stdout="benchmark/logs/comparators/digital_rads/{case_id}.radigest.stdout.log",
        stderr="benchmark/logs/comparators/digital_rads/{case_id}.radigest.stderr.log"
    params:
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        enzymes=case_enzymes_csv,
        min_size=case_min_size,
        max_size=case_max_size,
        threads=1
    shell:
        r"""
        mkdir -p results/comparators/digital_rads/raw benchmark/logs/comparators/digital_rads
        {params.radigest:q} \
          -fasta {input.ref:q} \
          -enzymes {params.enzymes:q} \
          -min {params.min_size} \
          -max {params.max_size} \
          -threads {params.threads} \
          -fragments-tsv {output.tsv:q} \
          -json {output.json:q} \
          > {log.stdout:q} 2> {log.stderr:q}
        """


rule normalize_radigest_for_digital_rads:
    input:
        "results/comparators/digital_rads/raw/{case_id}.radigest.fragments.tsv"
    output:
        "results/comparators/digital_rads/{case_id}.radigest.normalized.tsv"
    log:
        "benchmark/logs/comparators/digital_rads/{case_id}.normalize_radigest.log"
    shell:
        r"""
        mkdir -p results/comparators/digital_rads benchmark/logs/comparators/digital_rads
        python3 scripts/validation/normalize_radigest_tsv.py \
          --input {input:q} \
          --output {output:q} \
          --source-tool radigest \
          --hard-kept-only \
          > {log:q} 2>&1
        """


rule digital_rads_run:
    input:
        ref=case_reference,
        script=lambda wc: comparator_required_path("digital_rads"),
        enzymes="config/enzymes.tsv"
    output:
        raw="results/comparators/digital_rads/raw/{case_id}.digital_rads.raw.tsv",
        run_summary="results/comparators/digital_rads/raw/{case_id}.digital_rads.run_summary.tsv",
        version="results/comparators/digital_rads/raw/{case_id}.digital_rads.version.txt"
    log:
        stdout="benchmark/logs/comparators/digital_rads/{case_id}.digital_rads.stdout.log",
        stderr="benchmark/logs/comparators/digital_rads/{case_id}.digital_rads.stderr.log"
    params:
        workdir=lambda wc: f"results/comparators/digital_rads/work/{wc.case_id}",
        enzyme1=case_enzyme1,
        enzyme2=case_enzyme2,
        min_size=case_min_size,
        max_size=case_max_size
    shell:
        r"""
        mkdir -p results/comparators/digital_rads/raw benchmark/logs/comparators/digital_rads
        bash scripts/comparators/run_digital_rads.sh \
          --digital-rads {input.script:q} \
          --reference {input.ref:q} \
          --enzyme1 {params.enzyme1:q} \
          --enzyme2 {params.enzyme2:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --enzymes-tsv {input.enzymes:q} \
          --work-dir {params.workdir:q} \
          --raw-out {output.raw:q} \
          --summary-out {output.run_summary:q} \
          --version-out {output.version:q} \
          --stdout-log {log.stdout:q} \
          --stderr-log {log.stderr:q}
        """


rule normalize_digital_rads:
    input:
        raw="results/comparators/digital_rads/raw/{case_id}.digital_rads.raw.tsv",
        enzymes="config/enzymes.tsv"
    output:
        normalized="results/comparators/digital_rads/{case_id}.digital_rads.normalized.tsv",
        summary="results/comparators/digital_rads/{case_id}.digital_rads.normalize_summary.tsv"
    log:
        "benchmark/logs/comparators/digital_rads/{case_id}.normalize_digital_rads.log"
    params:
        enzyme1=case_enzyme1,
        enzyme2=case_enzyme2,
        min_size=case_min_size,
        max_size=case_max_size
    shell:
        r"""
        mkdir -p results/comparators/digital_rads benchmark/logs/comparators/digital_rads
        python3 scripts/comparators/normalize_digital_rads.py \
          --input {input.raw:q} \
          --output {output.normalized:q} \
          --summary {output.summary:q} \
          --enzymes-tsv {input.enzymes:q} \
          --enzyme1 {params.enzyme1:q} \
          --enzyme2 {params.enzyme2:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          > {log:q} 2>&1
        """


rule compare_radigest_digital_rads_intervals:
    input:
        first="results/comparators/digital_rads/{case_id}.radigest.normalized.tsv",
        second="results/comparators/digital_rads/{case_id}.digital_rads.normalized.tsv"
    output:
        summary="results/comparators/digital_rads/{case_id}.summary.tsv",
        matching="results/comparators/digital_rads/{case_id}.matching.tsv",
        only_first="results/comparators/digital_rads/{case_id}.only_first.tsv",
        only_second="results/comparators/digital_rads/{case_id}.only_second.tsv"
    log:
        "benchmark/logs/comparators/digital_rads/{case_id}.compare.log"
    params:
        prefix=lambda wc: f"results/comparators/digital_rads/{wc.case_id}"
    shell:
        r"""
        mkdir -p results/comparators/digital_rads benchmark/logs/comparators/digital_rads
        python3 scripts/validation/compare_interval_sets.py \
          --first {input.first:q} \
          --second {input.second:q} \
          --first-name radigest \
          --second-name Digital_RADs.py \
          --mode exact \
          --out-prefix {params.prefix:q} \
          --fail-on-difference \
          > {log:q} 2>&1
        """


rule ddradseqtools_rsitesearch:
    input:
        ref=case_reference,
        rsitesearch=lambda wc: comparator_required_path("ddradseqtools"),
        restrictionsites="external/ddRADseqTools/Package/restrictionsites.txt"
    output:
        frags="results/comparators/ddradseqtools/raw/{case_id}.fragments.fasta",
        stats="results/comparators/ddradseqtools/raw/{case_id}.fragments-stats.txt",
        run_summary="results/comparators/ddradseqtools/raw/{case_id}.run_summary.tsv",
        version="results/comparators/ddradseqtools/raw/{case_id}.version.txt"
    log:
        stdout="benchmark/logs/comparators/ddradseqtools/{case_id}.stdout.log",
        stderr="benchmark/logs/comparators/ddradseqtools/{case_id}.stderr.log"
    params:
        repo=ddradseqtools_repo,
        workdir=lambda wc: f"results/comparators/ddradseqtools/work/{wc.case_id}",
        enzyme1=case_enzyme1,
        enzyme2=case_enzyme2,
        min_size=case_min_size,
        max_size=ddradseqtools_tool_max_size
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/comparators/ddradseqtools/raw benchmark/logs/comparators/ddradseqtools
        bash scripts/comparators/run_ddradseqtools_rsitesearch.sh \
          --repo {params.repo:q} \
          --reference {input.ref:q} \
          --enzyme1 {params.enzyme1:q} \
          --enzyme2 {params.enzyme2:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --work-dir {params.workdir:q} \
          --frags-out {output.frags:q} \
          --stats-out {output.stats:q} \
          --summary-out {output.run_summary:q} \
          --version-out {output.version:q} \
          --stdout-log {log.stdout:q} \
          --stderr-log {log.stderr:q}
        """


rule normalize_ddradseqtools_intervals:
    input:
        frags="results/comparators/ddradseqtools/raw/{case_id}.fragments.fasta",
        enzymes="config/enzymes.tsv"
    output:
        normalized="results/comparators/ddradseqtools/{case_id}.ddradseqtools.normalized.tsv",
        summary="results/comparators/ddradseqtools/{case_id}.ddradseqtools.normalize_summary.tsv"
    log:
        "benchmark/logs/comparators/ddradseqtools/{case_id}.normalize_ddradseqtools.log"
    params:
        enzyme1=case_enzyme1,
        enzyme2=case_enzyme2,
        min_size=case_min_size,
        max_size=case_max_size
    shell:
        r"""
        mkdir -p results/comparators/ddradseqtools benchmark/logs/comparators/ddradseqtools
        python3 scripts/comparators/normalize_ddradseqtools_fragments.py \
          --frags {input.frags:q} \
          --enzymes-tsv {input.enzymes:q} \
          --enzyme1 {params.enzyme1:q} \
          --enzyme2 {params.enzyme2:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --seqid-mode first-token \
          --out {output.normalized:q} \
          --summary {output.summary:q} \
          > {log:q} 2>&1
        """


rule radigest_for_ddradseqtools:
    input:
        ref=case_reference
    output:
        json="results/comparators/ddradseqtools/raw/{case_id}.radigest.json",
        tsv="results/comparators/ddradseqtools/raw/{case_id}.radigest.fragments.tsv"
    log:
        stdout="benchmark/logs/comparators/ddradseqtools/{case_id}.radigest.stdout.log",
        stderr="benchmark/logs/comparators/ddradseqtools/{case_id}.radigest.stderr.log"
    params:
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        enzymes=case_enzymes_csv,
        min_size=case_min_size,
        max_size=case_max_size,
        threads=1
    shell:
        r"""
        mkdir -p results/comparators/ddradseqtools/raw benchmark/logs/comparators/ddradseqtools
        {params.radigest:q} \
          -fasta {input.ref:q} \
          -enzymes {params.enzymes:q} \
          -min {params.min_size} \
          -max {params.max_size} \
          -threads {params.threads} \
          -fragments-tsv {output.tsv:q} \
          -json {output.json:q} \
          > {log.stdout:q} 2> {log.stderr:q}
        """


rule normalize_radigest_for_ddradseqtools:
    input:
        "results/comparators/ddradseqtools/raw/{case_id}.radigest.fragments.tsv"
    output:
        "results/comparators/ddradseqtools/{case_id}.radigest.normalized.tsv"
    log:
        "benchmark/logs/comparators/ddradseqtools/{case_id}.normalize_radigest.log"
    shell:
        r"""
        mkdir -p results/comparators/ddradseqtools benchmark/logs/comparators/ddradseqtools
        python3 scripts/validation/normalize_radigest_tsv.py \
          --input {input:q} \
          --output {output:q} \
          --source-tool radigest \
          --hard-kept-only \
          > {log:q} 2>&1
        """


rule compare_radigest_ddradseqtools_intervals:
    input:
        radigest="results/comparators/ddradseqtools/{case_id}.radigest.normalized.tsv",
        ddradseqtools="results/comparators/ddradseqtools/{case_id}.ddradseqtools.normalized.tsv"
    output:
        summary="results/comparators/ddradseqtools/{case_id}.interval_compare.summary.tsv",
        matching="results/comparators/ddradseqtools/{case_id}.interval_compare.matching.tsv",
        only_first="results/comparators/ddradseqtools/{case_id}.interval_compare.only_first.tsv",
        only_second="results/comparators/ddradseqtools/{case_id}.interval_compare.only_second.tsv"
    log:
        "benchmark/logs/comparators/ddradseqtools/{case_id}.compare.log"
    params:
        prefix=lambda wc: f"results/comparators/ddradseqtools/{wc.case_id}.interval_compare"
    shell:
        r"""
        mkdir -p results/comparators/ddradseqtools benchmark/logs/comparators/ddradseqtools
        python3 scripts/validation/compare_interval_sets.py \
          --first {input.radigest:q} \
          --second {input.ddradseqtools:q} \
          --first-name radigest \
          --second-name DDRADSEQTOOLS_rsitesearch.py \
          --mode exact \
          --out-prefix {params.prefix:q} \
          --fail-on-difference \
          > {log:q} 2>&1
        """


rule build_comparator_interval_table:
    input:
        COMPARATOR_INTERVAL_OUTPUTS
    output:
        summary=COMPARATOR_CUT_EQUIVALENCE_SUMMARY,
        manuscript_table=COMPARATOR_INTERVAL_TABLE
    log:
        "benchmark/logs/comparators/cut_equivalence_table.log"
    shell:
        r"""
        mkdir -p results/comparators results/manuscript/tables benchmark/logs/comparators
        python3 scripts/comparators/build_cut_equivalence_table.py \
          --out {output.summary:q} \
          --manuscript-table {output.manuscript_table:q} \
          > {log:q} 2>&1
        """
