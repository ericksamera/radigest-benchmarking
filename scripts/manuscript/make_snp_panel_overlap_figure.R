#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(forcats)
  library(ggplot2)
  library(patchwork)
  library(readr)
  library(scales)
})

parse_args <- function(argv) {
  out <- list()
  i <- 1
  while (i <= length(argv)) {
    key <- argv[[i]]
    if (!startsWith(key, "--")) {
      stop("unexpected positional argument: ", key, call. = FALSE)
    }
    if (i == length(argv)) {
      stop("missing value for ", key, call. = FALSE)
    }
    out[[sub("^--", "", key)]] <- argv[[i + 1]]
    i <- i + 2
  }
  out
}

require_arg <- function(args, name) {
  value <- args[[name]]
  if (is.null(value) || identical(value, "")) {
    stop("missing required argument --", name, call. = FALSE)
  }
  value
}

as_num <- function(x) suppressWarnings(as.numeric(x))

args <- parse_args(commandArgs(trailingOnly = TRUE))
pairs_path <- require_arg(args, "pairs")
top_path <- require_arg(args, "top")
out_path <- require_arg(args, "out")
title <- args[["title"]]
if (is.null(title) || identical(title, "")) {
  title <- "Target-panel recovery across candidate enzyme pairs"
}

pairs <- read_tsv(pairs_path, show_col_types = FALSE, progress = FALSE) %>%
  mutate(
    panel_loci_read_accessible = as_num(panel_loci_read_accessible),
    panel_loci_captured = as_num(panel_loci_captured),
    panel_fraction_read_accessible = as_num(panel_fraction_read_accessible),
    off_panel_fragment_bp = as_num(off_panel_fragment_bp),
    predicted_mean_locus_depth = as_num(predicted_mean_locus_depth),
    predicted_weighted_genome_pct = as_num(predicted_weighted_genome_pct),
    feasible = tolower(as.character(feasible)) %in% c("true", "1", "yes", "pass", "feasible")
  )

top <- read_tsv(top_path, show_col_types = FALSE, progress = FALSE) %>%
  mutate(
    panel_loci_read_accessible = as_num(panel_loci_read_accessible),
    panel_loci_captured = as_num(panel_loci_captured),
    predicted_mean_locus_depth = as_num(predicted_mean_locus_depth),
    off_panel_fragment_bp = as_num(off_panel_fragment_bp)
  ) %>%
  slice_head(n = min(15, n()))

p1 <- ggplot(
  pairs,
  aes(
    x = off_panel_fragment_bp / 1e6,
    y = panel_loci_read_accessible,
    size = predicted_mean_locus_depth,
    shape = feasible
  )
) +
  geom_point(alpha = 0.75, na.rm = TRUE) +
  scale_size_continuous(name = "Predicted mean depth (×)", range = c(1.5, 5), na.value = 1.5) +
  labs(
    x = "Off-panel hard-window burden (Mbp)",
    y = "Read-accessible panel intervals",
    shape = "Feasible",
    title = "A. Panel recovery versus off-panel burden"
  ) +
  theme_bw(base_size = 9) +
  theme(legend.position = "bottom")

p2 <- ggplot(
  pairs,
  aes(
    x = predicted_mean_locus_depth,
    y = panel_loci_read_accessible,
    shape = feasible
  )
) +
  geom_point(alpha = 0.75, na.rm = TRUE) +
  labs(
    x = "Predicted mean locus depth (×)",
    y = "Read-accessible panel intervals",
    shape = "Feasible",
    title = "B. Panel recovery versus expected depth"
  ) +
  theme_bw(base_size = 9) +
  theme(legend.position = "bottom")

p3 <- ggplot(
  top,
  aes(
    x = panel_loci_read_accessible,
    y = fct_reorder(enzyme_pair, panel_loci_read_accessible)
  )
) +
  geom_col() +
  labs(
    x = "Read-accessible panel intervals",
    y = "Enzyme pair",
    title = "C. Top target-aware enzyme-pair rankings"
  ) +
  theme_bw(base_size = 9)

plot <- (p1 | p2) / p3 +
  plot_annotation(title = title)

dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
ggsave(out_path, plot, width = 8, height = 7, units = "in")
message("wrote ", out_path)
