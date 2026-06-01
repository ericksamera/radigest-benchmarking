#!/usr/bin/env Rscript

# Warm-session SimRAD benchmark.
#
# This script loads SimRAD once, then times repeated reference-based digest,
# adapter selection, and size-selection runs.
#
# It is intended to complement, not replace, cold command benchmarks.

usage <- function(status = 0) {
  cat(
    paste(
      "Usage:",
      "  Rscript scripts/benchmarks/run_simrad_warm_benchmark.R \\",
      "    --reference REF.fa[.gz] \\",
      "    --enzyme1 EcoRI \\",
      "    --enzyme2 MseI \\",
      "    --min 100 \\",
      "    --max 300 \\",
      "    --runs 5 \\",
      "    --enzymes-tsv config/enzymes.tsv \\",
      "    --out-runs results/tables/simrad_warm_runs.tsv \\",
      "    --out-summary results/tables/simrad_warm_summary.tsv \\",
      "    --version-log results/tables/simrad_warm_version.txt",
      "",
      "Options:",
      "  --reuse-reference   Load reference once and time only digest/select steps.",
      "",
      "Default:",
      "  The reference is re-read each timed run, but SimRAD and dependencies are",
      "  loaded once outside the timed loop.",
      sep = "\n"
    )
  )
  quit(status = status)
}

parse_args <- function(argv) {
  out <- list()
  i <- 1
  while (i <= length(argv)) {
    key <- argv[[i]]
    if (key %in% c("-h", "--help")) {
      usage(0)
    }
    if (!startsWith(key, "--")) {
      stop("unexpected positional argument: ", key)
    }

    name <- sub("^--", "", key)

    if (i == length(argv) || startsWith(argv[[i + 1]], "--")) {
      out[[name]] <- TRUE
      i <- i + 1
    } else {
      out[[name]] <- argv[[i + 1]]
      i <- i + 2
    }
  }
  out
}

require_arg <- function(args, name) {
  value <- args[[name]]
  if (is.null(value) || identical(value, TRUE) || identical(value, "")) {
    stop("missing required argument --", name)
  }
  value
}

is_true_flag <- function(args, name) {
  value <- args[[name]]
  isTRUE(value)
}

prepare_reference <- function(path) {
  if (!file.exists(path)) {
    stop("reference FASTA does not exist: ", path)
  }

  if (!grepl("\\.gz$", path)) {
    return(path)
  }

  tmp <- tempfile(pattern = "simrad_reference_", fileext = ".fa")
  in_con <- gzfile(path, open = "rt")
  out_con <- file(tmp, open = "wt")
  on.exit(close(in_con), add = TRUE)
  on.exit(close(out_con), add = TRUE)

  repeat {
    lines <- readLines(in_con, n = 100000L, warn = FALSE)
    if (length(lines) == 0L) {
      break
    }
    writeLines(lines, out_con)
  }

  tmp
}

read_enzyme_table <- function(path) {
  if (!file.exists(path)) {
    stop("enzyme table does not exist: ", path)
  }

  read.delim(
    path,
    sep = "\t",
    header = TRUE,
    stringsAsFactors = FALSE,
    check.names = FALSE,
    quote = "",
    comment.char = ""
  )
}

lookup_enzyme <- function(tbl, enzyme_name) {
  if (!"enzyme" %in% names(tbl)) {
    stop("enzyme table must contain column 'enzyme'")
  }

  motif_col <- if ("recognition_motif" %in% names(tbl)) {
    "recognition_motif"
  } else if ("motif" %in% names(tbl)) {
    "motif"
  } else {
    stop("enzyme table must contain 'recognition_motif' or 'motif'")
  }

  if (!"cut_offset" %in% names(tbl)) {
    stop("enzyme table must contain column 'cut_offset'")
  }

  hit <- tbl[tbl$enzyme == enzyme_name, , drop = FALSE]
  if (nrow(hit) != 1L) {
    stop("enzyme ", enzyme_name, " not found exactly once in enzyme table")
  }

  motif <- toupper(gsub("\\^", "", hit[[motif_col]][[1]]))
  cut_offset <- suppressWarnings(as.integer(hit[["cut_offset"]][[1]]))

  if (is.na(cut_offset)) {
    stop("cut_offset for enzyme ", enzyme_name, " is not an integer")
  }

  if (grepl("[^ACGT]", motif)) {
    stop(
      "SimRAD warm benchmark does not expand degenerate motif ",
      motif,
      " for enzyme ",
      enzyme_name
    )
  }

  if (cut_offset < 0L || cut_offset > nchar(motif)) {
    stop("cut_offset outside motif length for enzyme ", enzyme_name)
  }

  left <- if (cut_offset == 0L) "" else substr(motif, 1L, cut_offset)
  right <- if (cut_offset == nchar(motif)) "" else substr(
    motif,
    cut_offset + 1L,
    nchar(motif)
  )

  if (left == "" || right == "") {
    stop(
      "SimRAD warm benchmark does not support boundary cut split for enzyme ",
      enzyme_name
    )
  }

  list(
    name = enzyme_name,
    motif = motif,
    cut_offset = cut_offset,
    left = left,
    right = right
  )
}

fragment_lengths <- function(x) {
  if (length(x) == 0L) {
    return(integer(0))
  }
  nchar(as.character(x), type = "chars")
}

simrad_task <- function(reference_path, e1, e2, min_size, max_size, dna_reused = NULL) {
  dna <- dna_reused

  if (is.null(dna)) {
    ref_for_simrad <- prepare_reference(reference_path)
    dna <- SimRAD::ref.DNAseq(ref_for_simrad, subselect.contigs = FALSE)
  }

  digested <- SimRAD::insilico.digest(
    dna,
    e1$left,
    e1$right,
    e2$left,
    e2$right,
    verbose = FALSE
  )

  selected <- SimRAD::adapt.select(
    digested,
    type = "AB+BA",
    e1$left,
    e1$right,
    e2$left,
    e2$right
  )

  kept <- SimRAD::size.select(
    selected,
    min.size = min_size,
    max.size = max_size,
    graph = FALSE,
    verbose = FALSE
  )

  lens <- fragment_lengths(kept)

  list(
    digested_fragments = length(digested),
    adapter_selected_fragments = length(selected),
    size_selected_fragments = length(kept),
    total_bases = sum(lens),
    min_fragment_length = ifelse(length(lens) == 0L, NA_integer_, min(lens)),
    max_fragment_length = ifelse(length(lens) == 0L, NA_integer_, max(lens)),
    mean_fragment_length = ifelse(length(lens) == 0L, NA_real_, mean(lens))
  )
}

q1_q3 <- function(x) {
  x <- sort(x)
  n <- length(x)

  if (n == 0L) {
    return(c(NA_real_, NA_real_))
  }
  if (n == 1L) {
    return(c(x[[1]], x[[1]]))
  }
  if (n == 2L) {
    return(c(x[[1]], x[[2]]))
  }

  mid <- floor(n / 2L)
  if (n %% 2L == 0L) {
    lower <- x[seq_len(mid)]
    upper <- x[(mid + 1L):n]
  } else {
    lower <- x[seq_len(mid)]
    upper <- x[(mid + 2L):n]
  }

  c(stats::median(lower), stats::median(upper))
}

summary_row <- function(rows, reference, enzyme1, enzyme2, min_size, max_size, mode) {
  elapsed <- rows$elapsed_seconds
  user <- rows$user_seconds
  system <- rows$system_seconds
  fragments <- rows$size_selected_fragments
  bases <- rows$total_bases

  elapsed_q <- q1_q3(elapsed)

  data.frame(
    tool = "SimRAD",
    benchmark_mode = mode,
    reference = reference,
    enzyme1 = enzyme1,
    enzyme2 = enzyme2,
    min_size = min_size,
    max_size = max_size,
    runs = nrow(rows),
    median_elapsed_seconds = stats::median(elapsed),
    q1_elapsed_seconds = elapsed_q[[1]],
    q3_elapsed_seconds = elapsed_q[[2]],
    iqr_elapsed_seconds = elapsed_q[[2]] - elapsed_q[[1]],
    median_user_seconds = stats::median(user),
    median_system_seconds = stats::median(system),
    median_size_selected_fragments = stats::median(fragments),
    median_total_bases = stats::median(bases),
    notes = ifelse(
      mode == "reuse_reference",
      "SimRAD package and reference loaded once; timed loop includes digest/adapt/size-selection only",
      "SimRAD package loaded once; each timed run reloads reference and performs digest/adapt/size-selection"
    ),
    stringsAsFactors = FALSE
  )
}

write_version_log <- function(path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)

  sink(path)
  on.exit(sink(), add = TRUE)

  cat("SimRAD warm benchmark version log\n\n")
  cat("SimRAD version:\n")
  print(utils::packageVersion("SimRAD"))
  cat("\nSession info:\n")
  print(sessionInfo())
}

args <- tryCatch(parse_args(commandArgs(trailingOnly = TRUE)), error = function(e) {
  message("error: ", conditionMessage(e))
  usage(2)
})

reference <- require_arg(args, "reference")
enzyme1 <- require_arg(args, "enzyme1")
enzyme2 <- require_arg(args, "enzyme2")
min_size <- as.integer(require_arg(args, "min"))
max_size <- as.integer(require_arg(args, "max"))
runs <- as.integer(require_arg(args, "runs"))
enzymes_tsv <- require_arg(args, "enzymes-tsv")
out_runs <- require_arg(args, "out-runs")
out_summary <- require_arg(args, "out-summary")
version_log <- require_arg(args, "version-log")
reuse_reference <- is_true_flag(args, "reuse-reference")

if (is.na(min_size) || is.na(max_size) || min_size > max_size) {
  stop("--min and --max must be valid integers with min <= max")
}
if (is.na(runs) || runs < 1L) {
  stop("--runs must be a positive integer")
}

if (!requireNamespace("SimRAD", quietly = TRUE)) {
  stop("SimRAD is not installed")
}

suppressWarnings(suppressPackageStartupMessages(library(SimRAD)))

enzyme_table <- read_enzyme_table(enzymes_tsv)
e1 <- lookup_enzyme(enzyme_table, enzyme1)
e2 <- lookup_enzyme(enzyme_table, enzyme2)

dna_reused <- NULL
mode <- "warm_package_reload_reference"

if (reuse_reference) {
  mode <- "reuse_reference"
  ref_for_simrad <- prepare_reference(reference)
  dna_reused <- SimRAD::ref.DNAseq(ref_for_simrad, subselect.contigs = FALSE)
}

run_rows <- list()

for (i in seq_len(runs)) {
  gc(verbose = FALSE)

  result <- NULL
  timing <- system.time({
    result <- simrad_task(
      reference_path = reference,
      e1 = e1,
      e2 = e2,
      min_size = min_size,
      max_size = max_size,
      dna_reused = dna_reused
    )
  })

  run_rows[[i]] <- data.frame(
    tool = "SimRAD",
    benchmark_mode = mode,
    run = i,
    reference = reference,
    enzyme1 = enzyme1,
    enzyme2 = enzyme2,
    min_size = min_size,
    max_size = max_size,
    elapsed_seconds = unname(timing[["elapsed"]]),
    user_seconds = unname(timing[["user.self"]]),
    system_seconds = unname(timing[["sys.self"]]),
    digested_fragments = result$digested_fragments,
    adapter_selected_fragments = result$adapter_selected_fragments,
    size_selected_fragments = result$size_selected_fragments,
    total_bases = result$total_bases,
    min_fragment_length = result$min_fragment_length,
    max_fragment_length = result$max_fragment_length,
    mean_fragment_length = result$mean_fragment_length,
    stringsAsFactors = FALSE
  )
}

run_df <- do.call(rbind, run_rows)
summary_df <- summary_row(
  rows = run_df,
  reference = reference,
  enzyme1 = enzyme1,
  enzyme2 = enzyme2,
  min_size = min_size,
  max_size = max_size,
  mode = mode
)

dir.create(dirname(out_runs), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(out_summary), recursive = TRUE, showWarnings = FALSE)

write.table(
  run_df,
  file = out_runs,
  sep = "\t",
  quote = FALSE,
  row.names = FALSE
)

write.table(
  summary_df,
  file = out_summary,
  sep = "\t",
  quote = FALSE,
  row.names = FALSE
)

write_version_log(version_log)

message("wrote ", out_runs)
message("wrote ", out_summary)
message("wrote ", version_log)
