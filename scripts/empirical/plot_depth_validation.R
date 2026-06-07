#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(patchwork)
  library(readr)
  library(scales)
  library(stringr)
})

args <- commandArgs(trailingOnly = TRUE)

arg_value <- function(flag, default = NULL) {
  idx <- match(flag, args)
  if (is.na(idx)) {
    return(default)
  }
  if (idx == length(args) || startsWith(args[[idx + 1]], "--")) {
    stop("Missing value for ", flag, call. = FALSE)
  }
  args[[idx + 1]]
}

require_columns <- function(data, columns, label) {
  missing_columns <- setdiff(columns, names(data))
  if (length(missing_columns) > 0) {
    stop(label, " is missing required columns: ", paste(missing_columns, collapse = ", "), call. = FALSE)
  }
}

log_breaks_from_range <- function(values) {
  values <- values[is.finite(values) & values > 0]
  if (length(values) == 0) {
    return(c(0.1, 1, 10, 100))
  }
  lower_exp <- floor(log10(min(values)))
  upper_exp <- ceiling(log10(max(values)))
  10^(seq(lower_exp, upper_exp))
}

log_depth_labels <- function(values) {
  case_when(
    values >= 1 ~ format(values, trim = TRUE, scientific = FALSE),
    TRUE ~ format(values, trim = TRUE, scientific = FALSE, nsmall = 1)
  )
}

per_sample_path <- arg_value("--per-sample-depth")
summary_path <- arg_value("--summary")
out_path <- arg_value("--out")
formats <- str_split(arg_value("--formats", "pdf"), ",", simplify = TRUE) |>
  as.character() |>
  str_trim()
formats <- formats[formats != ""]

if (is.null(per_sample_path)) {
  stop("--per-sample-depth is required", call. = FALSE)
}
if (is.null(summary_path)) {
  stop("--summary is required", call. = FALSE)
}
if (is.null(out_path)) {
  stop("--out is required", call. = FALSE)
}

per_sample <- read_tsv(per_sample_path, show_col_types = FALSE, progress = FALSE)
summary <- read_tsv(summary_path, show_col_types = FALSE, progress = FALSE)

require_columns(
  per_sample,
  c("sample", "loci", "observed_read_pairs_at_loci", "mean_pairs_per_locus", "assigned_read_pair_fraction"),
  "per-sample depth table"
)
require_columns(
  summary,
  c(
    "library_id", "display_name", "enzyme_pair",
    "predicted_mean_locus_depth_at_budget",
    "modeled_read_pairs_per_sample",
    "mean_observed_pairs_per_locus",
    "median_observed_pairs_per_locus",
    "read_normalized_predicted_depth_mean_budget"
  ),
  "depth-validation summary table"
)

if (nrow(summary) != 1) {
  stop("depth-validation summary must contain exactly one row", call. = FALSE)
}

s <- summary[1, ]
predicted_budget_depth <- as.numeric(s$predicted_mean_locus_depth_at_budget)
modeled_reads_per_sample <- as.numeric(s$modeled_read_pairs_per_sample)
observed_mean_depth <- as.numeric(s$mean_observed_pairs_per_locus)
observed_median_depth <- as.numeric(s$median_observed_pairs_per_locus)
read_normalized_prediction <- as.numeric(s$read_normalized_predicted_depth_mean_budget)

if (!all(is.finite(c(predicted_budget_depth, modeled_reads_per_sample, observed_mean_depth, observed_median_depth, read_normalized_prediction)))) {
  stop("summary table contains non-finite prediction or observed-depth values", call. = FALSE)
}
if (modeled_reads_per_sample <= 0) {
  stop("modeled_read_pairs_per_sample must be positive", call. = FALSE)
}

plot_df <- per_sample |>
  mutate(
    observed_read_pairs_at_loci = as.numeric(observed_read_pairs_at_loci),
    mean_pairs_per_locus = as.numeric(mean_pairs_per_locus),
    assigned_read_pair_fraction = as.numeric(assigned_read_pair_fraction),
    sample_label = basename(sample)
  ) |>
  filter(
    is.finite(observed_read_pairs_at_loci),
    is.finite(mean_pairs_per_locus),
    mean_pairs_per_locus > 0,
    observed_read_pairs_at_loci > 0
  ) |>
  mutate(
    read_normalized_predicted_depth = predicted_budget_depth * observed_read_pairs_at_loci / modeled_reads_per_sample
  ) |>
  filter(is.finite(read_normalized_predicted_depth), read_normalized_predicted_depth > 0) |>
  arrange(mean_pairs_per_locus, sample_label) |>
  mutate(sample_order = row_number())

if (nrow(plot_df) == 0) {
  stop("No finite positive per-sample depth rows to plot", call. = FALSE)
}

line_df <- tibble(
  label = c(
    sprintf("Budget pred. %.1fx", predicted_budget_depth),
    sprintf("Read-norm. %.1fx", read_normalized_prediction),
    sprintf("Median %.1fx", observed_median_depth)
  ),
  depth = c(predicted_budget_depth, read_normalized_prediction, observed_median_depth),
  line_type = c("solid", "longdash", "dotted")
)

depth_breaks <- log_breaks_from_range(c(
  plot_df$mean_pairs_per_locus,
  plot_df$read_normalized_predicted_depth,
  predicted_budget_depth,
  observed_median_depth,
  read_normalized_prediction
))
depth_limits <- range(depth_breaks, na.rm = TRUE)
sample_label_x <- max(plot_df$sample_order) + 3
line_label_df <- line_df |>
  mutate(x = sample_label_x)

p_sorted <- ggplot(plot_df, aes(x = sample_order, y = mean_pairs_per_locus)) +
  geom_point(color = "#2B5CAD", size = 1.5, alpha = 0.82) +
  geom_hline(data = line_df, aes(yintercept = depth, linetype = line_type), color = "grey15", linewidth = 0.45, show.legend = FALSE) +
  geom_label(
    data = line_label_df,
    aes(x = x, y = depth, label = label),
    inherit.aes = FALSE,
    hjust = 1,
    size = 2.4,
    label.size = 0.15,
    label.padding = unit(0.11, "lines"),
    fill = "white",
    color = "grey15"
  ) +
  scale_linetype_identity() +
  scale_y_log10(
    breaks = depth_breaks,
    labels = log_depth_labels,
    limits = depth_limits
  ) +
  scale_x_continuous(
    breaks = pretty_breaks(n = 8),
    limits = c(1, sample_label_x),
    expand = expansion(mult = c(0.01, 0.02))
  ) +
  coord_cartesian(clip = "off") +
  labs(
    x = "Sample (sorted by observed depth)",
    y = "Observed mean locus depth"
  ) +
  theme_minimal(base_size = 9) +
  theme(
    panel.grid.minor = element_blank(),
    plot.margin = margin(5.5, 8, 5.5, 12)
  )

p_calibration <- ggplot(
  plot_df,
  aes(x = read_normalized_predicted_depth, y = mean_pairs_per_locus)
) +
  geom_point(color = "#2B5CAD", size = 1.6, alpha = 0.82) +
  geom_abline(intercept = 0, slope = 1, linetype = "longdash", color = "grey15", linewidth = 0.45) +
  scale_x_log10(
    breaks = depth_breaks,
    labels = log_depth_labels,
    limits = depth_limits
  ) +
  scale_y_log10(
    breaks = depth_breaks,
    labels = log_depth_labels,
    limits = depth_limits
  ) +
  coord_equal() +
  labs(
    x = "Read-normalized predicted depth",
    y = "Observed mean locus depth"
  ) +
  theme_minimal(base_size = 9) +
  theme(
    panel.grid.minor = element_blank(),
    plot.margin = margin(5.5, 8, 5.5, 12)
  )

combined <- (p_sorted | p_calibration) +
  plot_layout(widths = c(1.8, 1.1)) +
  plot_annotation(tag_levels = "A") &
  theme(
    plot.tag = element_text(face = "bold", size = 13),
    plot.tag.position = "topleft",
    plot.tag.location = "margin"
  )

base_stem <- tools::file_path_sans_ext(out_path)
out_ext <- tools::file_ext(out_path)
if (identical(out_ext, "")) {
  requested_outputs <- file.path(dirname(out_path), paste0(basename(out_path), ".", formats))
} else if (length(formats) == 1 && identical(tolower(out_ext), tolower(formats[[1]]))) {
  requested_outputs <- out_path
} else {
  requested_outputs <- paste0(base_stem, ".", formats)
}

for (output in requested_outputs) {
  dir.create(dirname(output), recursive = TRUE, showWarnings = FALSE)
  fmt <- tolower(tools::file_ext(output))
  if (identical(fmt, "pdf") && isTRUE(capabilities("cairo"))) {
    ggsave(output, plot = combined, width = 7.4, height = 3.6, device = cairo_pdf)
  } else {
    ggsave(output, plot = combined, width = 7.4, height = 3.6)
  }
}
