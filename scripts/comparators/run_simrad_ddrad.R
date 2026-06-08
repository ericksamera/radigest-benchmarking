#!/usr/bin/env Rscript

# Run SimRAD for a matched digest/size-selection count comparison.
#
# This wrapper intentionally outputs aggregate count-level metrics only.
# SimRAD does not expose coordinate-resolved intervals equivalent to radigest
# fragment TSV/GFF3 outputs.
#
# Example:
#   Rscript scripts/comparators/run_simrad_ddrad.R \
#     --reference ref.fa \
#     --enzyme1 EcoRI \
#     --enzyme2 MseI \
#     --min 100 \
#     --max 300 \
#     --enzymes-tsv config/enzymes.tsv \
#     --out results/raw/comparators/simrad/example.tsv \
#     --version-log results/raw/comparators/simrad/example.version.txt

usage <- function(status = 0) {
  cat(
    paste(
      "Usage:",
      "  Rscript scripts/comparators/run_simrad_ddrad.R \\",
      "    --reference REF.fa[.gz] \\",
      "    --enzyme1 ENZ1 \\",
      "    [--enzyme2 ENZ2|NA] \\",
      "    --min MIN \\",
      "    --max MAX \\",
      "    --enzymes-tsv config/enzymes.tsv \\",
      "    --out OUT.tsv \\",
      "    --version-log VERSION.txt \\",
      "    [--adapter-type AB+BA]",
      "",
      "Notes:",
      "  - Double-digest comparisons use SimRAD adapt.select(type='AB+BA') by default.",
      "  - Single-enzyme comparisons skip adapt.select.",
      "  - The wrapper fails on degenerate motifs such as ApeKI GCWGC; expand them manually if needed.",
      "  - The wrapper warns for multi-record FASTA because SimRAD ref.DNAseq concatenates records.",
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

count_fasta_records <- function(path) {
  con <- if (grepl("\\.gz$", path)) {
    gzfile(path, open = "rt")
  } else {
    file(path, open = "rt")
  }
  on.exit(close(con), add = TRUE)

  n <- 0L
  repeat {
    lines <- readLines(con, n = 100000L, warn = FALSE)
    if (length(lines) == 0L) {
      break
    }
    n <- n + sum(startsWith(lines, ">"))
  }
  n
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
  name_col <- if ("enzyme_id" %in% names(tbl)) {
    "enzyme_id"
  } else if ("enzyme" %in% names(tbl)) {
    "enzyme"
  } else {
    stop("enzyme table must contain column 'enzyme_id' or 'enzyme'")
  }

  motif_col <- if ("recognition_sequence" %in% names(tbl)) {
    "recognition_sequence"
  } else if ("recognition_motif" %in% names(tbl)) {
    "recognition_motif"
  } else if ("motif" %in% names(tbl)) {
    "motif"
  } else {
    stop("enzyme table must contain 'recognition_sequence', 'recognition_motif', or 'motif'")
  }

  if (!"cut_offset" %in% names(tbl)) {
    stop("enzyme table must contain column 'cut_offset'")
  }

  hit <- tbl[tbl[[name_col]] == enzyme_name, , drop = FALSE]
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
      "SimRAD wrapper does not automatically expand degenerate motif ",
      motif,
      " for enzyme ",
      enzyme_name,
      ". Use an unambiguous enzyme or add a dedicated expansion workflow."
    )
  }

  if (cut_offset < 0L || cut_offset > nchar(motif)) {
    stop(
      "cut_offset for enzyme ",
      enzyme_name,
      " is outside motif length: ",
      cut_offset,
      " vs ",
      nchar(motif)
    )
  }

  left <- if (cut_offset == 0L) "" else substr(motif, 1L, cut_offset)
  right <- if (cut_offset == nchar(motif)) "" else substr(motif, cut_offset + 1L, nchar(motif))

  if (left == "" || right == "") {
    stop(
      "SimRAD wrapper does not support cut offsets at motif boundaries for enzyme ",
      enzyme_name,
      " (caret-form split would be empty on one side)."
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

write_version_log <- function(path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  sink(path)
  on.exit(sink(), add = TRUE)

  cat("SimRAD version:\n")
  print(packageVersion("SimRAD"))
  cat("\nSession info:\n")
  print(sessionInfo())
}

args <- tryCatch(parse_args(commandArgs(trailingOnly = TRUE)), error = function(e) {
  message("error: ", conditionMessage(e))
  usage(2)
})

reference <- require_arg(args, "reference")
enzyme1 <- require_arg(args, "enzyme1")
enzyme2 <- args[["enzyme2"]]
if (is.null(enzyme2) || enzyme2 %in% c("", "NA", "none", "NONE", "null", "NULL")) {
  enzyme2 <- NA_character_
}
min_size <- as.integer(require_arg(args, "min"))
max_size <- as.integer(require_arg(args, "max"))
enzymes_tsv <- require_arg(args, "enzymes-tsv")
out_path <- require_arg(args, "out")
version_log <- require_arg(args, "version-log")
adapter_type <- args[["adapter-type"]]
if (is.null(adapter_type) || identical(adapter_type, TRUE)) {
  adapter_type <- "AB+BA"
}

if (is.na(min_size) || is.na(max_size)) {
  stop("--min and --max must be integers")
}
if (min_size > max_size) {
  stop("--min must be <= --max")
}

if (!requireNamespace("SimRAD", quietly = TRUE)) {
  stop(
    "R package SimRAD is not installed. Run: ",
    "Rscript scripts/comparators/install_simrad_archive.R"
  )
}

suppressPackageStartupMessages(library(SimRAD))

enzyme_table <- read_enzyme_table(enzymes_tsv)
e1 <- lookup_enzyme(enzyme_table, enzyme1)
e2 <- if (is.na(enzyme2)) NULL else lookup_enzyme(enzyme_table, enzyme2)

notes <- character()
fasta_records <- count_fasta_records(reference)
if (fasta_records > 1L) {
  notes <- c(
    notes,
    "multi-record FASTA: SimRAD ref.DNAseq concatenates records; count-level comparison may differ from per-record digest engines"
  )
}
if (grepl("\\.gz$", reference)) {
  notes <- c(notes, "gzipped FASTA was decompressed to a temporary plain FASTA for SimRAD")
}

reference_for_simrad <- prepare_reference(reference)

message("Loading reference with SimRAD::ref.DNAseq(subselect.contigs = FALSE)")
dna <- SimRAD::ref.DNAseq(reference_for_simrad, subselect.contigs = FALSE)

message("Running SimRAD digestion")
if (is.null(e2)) {
  digested <- SimRAD::insilico.digest(
    dna,
    e1$left,
    e1$right,
    verbose = FALSE
  )
  adapter_selected <- digested
  adapter_selected_count <- length(adapter_selected)
} else {
  digested <- SimRAD::insilico.digest(
    dna,
    e1$left,
    e1$right,
    e2$left,
    e2$right,
    verbose = FALSE
  )
  adapter_selected <- SimRAD::adapt.select(
    digested,
    type = adapter_type,
    e1$left,
    e1$right,
    e2$left,
    e2$right
  )
  adapter_selected_count <- length(adapter_selected)
}

message("Running SimRAD size selection")
kept <- SimRAD::size.select(
  adapter_selected,
  min.size = min_size,
  max.size = max_size,
  graph = FALSE,
  verbose = FALSE
)

lens <- fragment_lengths(kept)

result <- data.frame(
  tool = "SimRAD",
  reference = reference,
  fasta_records = fasta_records,
  enzyme1 = enzyme1,
  enzyme2 = ifelse(is.null(e2), "", enzyme2),
  enzyme1_left = e1$left,
  enzyme1_right = e1$right,
  enzyme2_left = ifelse(is.null(e2), "", e2$left),
  enzyme2_right = ifelse(is.null(e2), "", e2$right),
  min_size = min_size,
  max_size = max_size,
  adapter_type = ifelse(is.null(e2), "", adapter_type),
  digested_fragments = length(digested),
  adapter_selected_fragments = adapter_selected_count,
  size_selected_fragments = length(kept),
  total_bases = sum(lens),
  min_fragment_length = ifelse(length(lens) == 0L, "", min(lens)),
  max_fragment_length = ifelse(length(lens) == 0L, "", max(lens)),
  mean_fragment_length = ifelse(length(lens) == 0L, "", mean(lens)),
  median_fragment_length = ifelse(length(lens) == 0L, "", median(lens)),
  notes = paste(notes, collapse = "; "),
  stringsAsFactors = FALSE
)

dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
write.table(
  result,
  file = out_path,
  sep = "\t",
  quote = FALSE,
  row.names = FALSE
)

write_version_log(version_log)

message("Wrote: ", out_path)
message("Wrote: ", version_log)
