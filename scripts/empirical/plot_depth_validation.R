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

clean_log_axis <- function(values, lower_floor = 0.01, upper_ceiling = 100, lower_pad = 0.85) {
  values <- values[is.finite(values) & values > 0]
  if (length(values) == 0) {
    return(list(limits = c(lower_floor, upper_ceiling), breaks = c(lower_floor, 0.1, 1, 10, upper_ceiling)))
  }

  observed_min <- min(values)
  lower_limit <- if (observed_min < lower_floor) observed_min * lower_pad else lower_floor
  lower_limit <- max(lower_limit, .Machine$double.eps)
  upper_limit <- upper_ceiling
  if (!is.finite(upper_limit) || upper_limit <= lower_limit) {
    upper_limit <- max(values) * 1.10
  }

  candidate_breaks <- 10^(seq(floor(log10(lower_limit)), ceiling(log10(upper_limit))))
  breaks <- candidate_breaks[candidate_breaks >= lower_limit & candidate_breaks <= upper_limit]
  if (length(breaks) == 0) {
    breaks <- c(lower_limit, upper_limit)
  }

  list(limits = c(lower_limit, upper_limit), breaks = breaks)
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
per_locus_path <- arg_value("--per-locus-depth")
summary_path <- arg_value("--summary")
out_path <- arg_value("--out")
formats <- str_split(arg_value("--formats", "pdf"), ",", simplify = TRUE) |>
  as.character() |>
  str_trim()
formats <- formats[formats != ""]

if (is.null(per_sample_path)) {
  stop("--per-sample-depth is required", call. = FALSE)
}
if (is.null(per_locus_path)) {
  stop("--per-locus-depth is required", call. = FALSE)
}
if (is.null(summary_path)) {
  stop("--summary is required", call. = FALSE)
}
if (is.null(out_path)) {
  stop("--out is required", call. = FALSE)
}

per_sample <- read_tsv(per_sample_path, show_col_types = FALSE, progress = FALSE)
per_locus <- read_tsv(per_locus_path, show_col_types = FALSE, progress = FALSE)
summary <- read_tsv(summary_path, show_col_types = FALSE, progress = FALSE)

require_columns(
  per_sample,
  c("sample", "loci", "observed_read_pairs_at_loci", "mean_pairs_per_locus", "assigned_read_pair_fraction"),
  "per-sample depth table"
)
require_columns(
  per_locus,
  c("locus_index", "mean_pairs_per_sample"),
  "per-locus depth table"
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

locus_df <- per_locus |>
  mutate(mean_pairs_per_sample = as.numeric(mean_pairs_per_sample)) |>
  filter(is.finite(mean_pairs_per_sample), mean_pairs_per_sample >= 0)

if (nrow(locus_df) == 0) {
  stop("No finite per-locus depth rows to plot", call. = FALSE)
}

positive_locus_df <- locus_df |>
  filter(mean_pairs_per_sample > 0)

if (nrow(positive_locus_df) == 0) {
  stop("No positive per-locus depth values to plot on a log scale", call. = FALSE)
}

total_loci <- nrow(locus_df)
ccdf_df <- positive_locus_df |>
  count(mean_pairs_per_sample, name = "n") |>
  arrange(desc(mean_pairs_per_sample)) |>
  mutate(fraction_at_or_above = cumsum(n) / total_loci) |>
  arrange(mean_pairs_per_sample)

threshold_df <- tibble(threshold = c(1, 3, 5, 10)) |>
  mutate(
    fraction_at_or_above = vapply(
      threshold,
      function(x) mean(locus_df$mean_pairs_per_sample >= x),
      numeric(1)
    ),
    label = paste0(threshold, "x"),
    label_x = threshold * 1.06,
    label_y = case_when(
      threshold == 1 ~ 0.985,
      TRUE ~ pmin(fraction_at_or_above + 0.04, 0.94)
    )
  )

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

sample_depth_axis <- clean_log_axis(
  c(
    plot_df$mean_pairs_per_locus,
    predicted_budget_depth,
    observed_median_depth,
    read_normalized_prediction
  ),
  lower_floor = 0.01,
  upper_ceiling = 100
)
locus_depth_axis <- clean_log_axis(
  c(
    positive_locus_df$mean_pairs_per_sample,
    threshold_df$threshold
  ),
  lower_floor = 0.01,
  upper_ceiling = 100
)

p_sorted <- ggplot(plot_df, aes(x = sample_order, y = mean_pairs_per_locus)) +
  geom_point(color = "#2B5CAD", size = 1.25, alpha = 0.82) +
  geom_hline(data = line_df, aes(yintercept = depth, linetype = label), color = "grey15", linewidth = 0.45) +
  scale_linetype_manual(values = setNames(line_df$line_type, line_df$label)) +
  scale_y_log10(
    breaks = sample_depth_axis$breaks,
    labels = log_depth_labels
  ) +
  coord_cartesian(ylim = sample_depth_axis$limits) +
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

p_locus_distribution <- ggplot(ccdf_df, aes(x = mean_pairs_per_sample, y = fraction_at_or_above)) +
  geom_step(color = "#2B5CAD", linewidth = 0.55, direction = "hv") +
  geom_vline(xintercept = threshold_df$threshold, linetype = "dotted", color = "grey40", linewidth = 0.35) +
  geom_point(data = threshold_df, aes(x = threshold, y = fraction_at_or_above), color = "grey20", size = 1.3) +
  geom_text(
    data = threshold_df,
    aes(x = label_x, y = label_y, label = label),
    size = 2.2,
    hjust = 0,
    vjust = 0.5
  ) +
  scale_x_log10(
    breaks = locus_depth_axis$breaks,
    labels = log_depth_labels
  ) +
  coord_cartesian(xlim = locus_depth_axis$limits) +
  scale_y_continuous(
    labels = percent_format(accuracy = 1),
    limits = c(0, 1),
    breaks = pretty_breaks(n = 5),
    expand = expansion(mult = c(0.01, 0.05))
  ) +
  labs(
    x = "Observed mean depth per locus",
    y = "Predicted loci at or above depth"
  ) +
  theme_minimal(base_size = 8) +
  theme(
    panel.grid.minor = element_blank(),
    axis.title = element_text(size = 8.5),
    axis.text = element_text(size = 7),
    plot.margin = margin(5.5, 8, 5.5, 12)
  )

combined <- (p_sorted | p_locus_distribution) +
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
