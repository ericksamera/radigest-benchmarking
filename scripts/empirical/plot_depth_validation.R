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
  vapply(
    values,
    function(value) {
      if (!is.finite(value)) {
        return("")
      }
      if (value >= 1) {
        return(formatC(value, format = "f", digits = 0))
      }
      digits <- max(1, ceiling(-log10(value)))
      formatC(value, format = "f", digits = digits)
    },
    character(1)
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
    sprintf("Predicted at modeled budget (%.1fx)", predicted_budget_depth),
    sprintf("Read-normalized prediction (%.1fx)", read_normalized_prediction),
    sprintf("Observed median (%.1fx)", observed_median_depth)
  ),
  depth = c(predicted_budget_depth, read_normalized_prediction, observed_median_depth),
  line_type = c("solid", "longdash", "dotted")
)
line_df$label <- factor(line_df$label, levels = line_df$label)

depth_breaks <- log_breaks_from_range(c(
  plot_df$mean_pairs_per_locus,
  plot_df$read_normalized_predicted_depth,
  predicted_budget_depth,
  observed_median_depth,
  read_normalized_prediction
))
depth_limits <- range(depth_breaks, na.rm = TRUE)

p_sorted <- ggplot(plot_df, aes(x = sample_order, y = mean_pairs_per_locus)) +
  geom_point(color = "#2B5CAD", size = 1.25, alpha = 0.82) +
  geom_hline(data = line_df, aes(yintercept = depth, linetype = label), color = "grey15", linewidth = 0.45) +
  scale_linetype_manual(values = setNames(line_df$line_type, line_df$label)) +
  scale_y_log10(
    breaks = depth_breaks,
    labels = log_depth_labels,
    limits = depth_limits
  ) +
  scale_x_continuous(
    breaks = pretty_breaks(n = 8),
    expand = expansion(mult = c(0.01, 0.02))
  ) +
  labs(
    x = "Sample (sorted by observed depth)",
    y = "Observed mean locus depth",
    linetype = NULL
  ) +
  theme_minimal(base_size = 8) +
  theme(
    panel.grid.minor = element_blank(),
    axis.title = element_text(size = 8.5),
    axis.text = element_text(size = 7),
    legend.position = "bottom",
    legend.direction = "horizontal",
    legend.box = "horizontal",
    legend.text = element_text(size = 7),
    legend.key.width = unit(1.0, "lines"),
    plot.margin = margin(5.5, 8, 5.5, 12)
  )

p_calibration <- ggplot(
  plot_df,
  aes(x = read_normalized_predicted_depth, y = mean_pairs_per_locus)
) +
  geom_point(color = "#2B5CAD", size = 1.25, alpha = 0.82) +
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
  labs(
    x = "Read-normalized predicted depth",
    y = "Observed mean locus depth"
  ) +
  theme_minimal(base_size = 8) +
  theme(
    panel.grid.minor = element_blank(),
    axis.title = element_text(size = 8.5),
    axis.text = element_text(size = 7),
    plot.margin = margin(5.5, 8, 5.5, 12)
  )

combined <- (p_sorted | p_calibration) +
  plot_layout(widths = c(1.55, 1.25), guides = "collect") +
  plot_annotation(tag_levels = "A") &
  theme(
    plot.tag = element_text(face = "bold", size = 12),
    plot.tag.position = "topleft",
    plot.tag.location = "margin",
    legend.position = "bottom"
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
    ggsave(output, plot = combined, width = 8.2, height = 3.9, device = cairo_pdf)
  } else {
    ggsave(output, plot = combined, width = 8.2, height = 3.9)
  }
}
