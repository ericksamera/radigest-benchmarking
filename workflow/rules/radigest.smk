# Local radigest source acquisition and build rules.
# Builds the primary radigest binary, radigest-design, and developer cached
# pair-screening and phase-timed benchmark helpers into .local/bin so Makefile targets can run without
# repeated RADIGEST overrides.

RADIGEST_REPO_DIR = config.get("radigest_source_dir", "external/radigest")
RADIGEST_SOURCE_MARKER = f"{RADIGEST_REPO_DIR}/.benchmark_checkout_complete"
LOCAL_BIN_DIR = config.get("local_bin_dir", ".local/bin")
RADIGEST_SOURCE_COMMIT = ".local/radigest/source_commit.txt"
RADIGEST_BUILD_INFO = ".local/radigest/build_info.tsv"
RADIGEST_LOCAL_BIN = f"{LOCAL_BIN_DIR}/radigest"
RADIGEST_LOCAL_SCREEN_PAIRS_CACHED = f"{LOCAL_BIN_DIR}/radigest-screen-pairs-cached"
RADIGEST_LOCAL_BENCH_SCREEN_CACHED = f"{LOCAL_BIN_DIR}/radigest-bench-screen-cached"
RADIGEST_LOCAL_DESIGN = f"{LOCAL_BIN_DIR}/radigest-design"
RADIGEST_BUILD_OUTPUTS = [
    RADIGEST_LOCAL_BIN,
    RADIGEST_LOCAL_SCREEN_PAIRS_CACHED,
    RADIGEST_LOCAL_BENCH_SCREEN_CACHED,
    RADIGEST_LOCAL_DESIGN,
    RADIGEST_BUILD_INFO,
]


rule radigest_checkout:
    output:
        marker=touch(RADIGEST_SOURCE_MARKER),
        commit=RADIGEST_SOURCE_COMMIT,
    log:
        "benchmark/logs/radigest/checkout.log",
    conda:
        "../envs/radigest-build.yml"
    params:
        repo=lambda wildcards: config.get(
            "radigest_repo",
            config.get(
                "radigest_git_url", "https://github.com/ericksamera/radigest.git"
            ),
        ),
        ref=lambda wildcards: config.get(
            "radigest_ref", config.get("radigest_git_ref", "main")
        ),
        repo_dir=RADIGEST_REPO_DIR,
    shell:
        r"""
        mkdir -p external .local/radigest benchmark/logs/radigest
        if [ ! -d {params.repo_dir:q}/.git ]; then
            rm -rf {params.repo_dir:q}
            git clone {params.repo:q} {params.repo_dir:q} >{log:q} 2>&1
        else
            git -C {params.repo_dir:q} remote set-url origin {params.repo:q} >>{log:q} 2>&1
            git -C {params.repo_dir:q} fetch --tags origin >>{log:q} 2>&1
        fi
        git -C {params.repo_dir:q} fetch --tags origin >>{log:q} 2>&1
        git -C {params.repo_dir:q} checkout {params.ref:q} >>{log:q} 2>&1
        git -C {params.repo_dir:q} submodule update --init --recursive >>{log:q} 2>&1
        git -C {params.repo_dir:q} rev-parse HEAD >{output.commit:q}
        """


rule build_local_radigest:
    input:
        marker=RADIGEST_SOURCE_MARKER,
        commit=RADIGEST_SOURCE_COMMIT,
    output:
        radigest=RADIGEST_LOCAL_BIN,
        screen_pairs_cached=RADIGEST_LOCAL_SCREEN_PAIRS_CACHED,
        bench_screen_cached=RADIGEST_LOCAL_BENCH_SCREEN_CACHED,
        design=RADIGEST_LOCAL_DESIGN,
        build_info=RADIGEST_BUILD_INFO,
    log:
        "benchmark/logs/radigest/build.log",
    conda:
        "../envs/radigest-build.yml"
    params:
        repo_dir=RADIGEST_REPO_DIR,
        bin_dir=LOCAL_BIN_DIR,
    shell:
        r"""
        mkdir -p {params.bin_dir:q} .local/radigest benchmark/logs/radigest
        make -C {params.repo_dir:q} build-dev BIN_DIR="$PWD/{params.bin_dir}" >{log:q} 2>&1
        test -x {output.radigest:q}
        test -x {output.screen_pairs_cached:q}
        test -x {output.bench_screen_cached:q}
        test -x {output.design:q}
        {{
                                  printf 'field\tvalue\n'
                                  printf 'repo_dir\t%s\n' {params.repo_dir:q}
                                  printf 'source_commit\t%s\n' "$(cat {input.commit:q})"
                                  printf 'radigest\t%s\n' {output.radigest:q}
                                  printf 'radigest_version\t%s\n' "$({output.radigest:q} --version 2>/dev/null || true)"
                                  printf 'screen_pairs_cached\t%s\n' {output.screen_pairs_cached:q}
                                  printf 'screen_pairs_cached_version\t%s\n' "$({output.screen_pairs_cached:q} --version 2>/dev/null || true)"
                                  printf 'radigest_bench_screen_cached\t%s\n' {output.bench_screen_cached:q}
                                  printf 'radigest_bench_screen_cached_version\t%s\n' "$({output.bench_screen_cached:q} --version 2>/dev/null || true)"
                                  printf 'radigest_design\t%s\n' {output.design:q}
                                  printf 'radigest_design_version\t%s\n' "$({output.design:q} --version 2>/dev/null || true)"
                                }} >{output.build_info:q}
        """
