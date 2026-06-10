#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(forcats)
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

model_family_label <- function(model) {
  case_when(
    model == "none" ~ "Raw digest",
    model == "hard" ~ "Hard window",
    model == "soft-window" ~ "Soft window",
    model == "soft-window-short-bias" ~ "Soft + short-bias",
    model == "normal" ~ "Normal",
    model == "triangular" ~ "Triangular",
    TRUE ~ model
  )
}

dataset_label <- function(library_id, display_name) {
  case_when(
    library_id == "sockeye_ecori_msei" ~ "Sockeye\nEcoRI-MseI",
    library_id == "anopheles_ecori_msei" ~ "Anopheles\nEcoRI-MseI",
    library_id == "rhododendron_dpnII_mspI" ~ "Rhododendron\nDpnII-MspI",
    TRUE ~ str_replace_all(display_name, "\\s+", "\n")
  )
}

ranking_path <- arg_value("--ranking")
out_path <- arg_value("--out")
formats <- str_split(arg_value("--formats", "pdf"), ",", simplify = TRUE) |>
  as.character() |>
  str_trim()
formats <- formats[formats != ""]

if (is.null(ranking_path)) {
  stop("--ranking is required", call. = FALSE)
}
if (is.null(out_path)) {
  stop("--out is required", call. = FALSE)
}

ranking <- read_tsv(ranking_path, show_col_types = FALSE, progress = FALSE)

required_columns <- c(
  "library_id", "display_name", "model", "js_read",
  "pred_in_window_fraction", "obs_in_window_fraction"
)
missing_columns <- setdiff(required_columns, names(ranking))
if (length(missing_columns) > 0) {
  stop(
    "Missing columns in size-model ranking table: ",
    paste(missing_columns, collapse = ", "),
    call. = FALSE
  )
}

if (!("model_family" %in% names(ranking))) {
  ranking <- ranking |>
    mutate(model_family = model_family_label(model))
}

model_order <- c(
  "Raw digest", "Hard window", "Soft window", "Soft + short-bias",
  "Normal", "Triangular"
)

dataset_order <- c(
  "sockeye_ecori_msei",
  "anopheles_ecori_msei",
  "rhododendron_dpnII_mspI"
)

known_dataset_labels <- dataset_label(dataset_order, dataset_order)

plot_df <- ranking |>
  mutate(
    js_read = as.numeric(js_read),
    pred_in_window_fraction = as.numeric(pred_in_window_fraction),
    obs_in_window_fraction = as.numeric(obs_in_window_fraction),
    dataset = dataset_label(library_id, display_name),
    model_family = as.character(model_family),
    model_family = factor(model_family, levels = model_order)
  ) |>
  filter(!is.na(model_family), is.finite(js_read))

if (nrow(plot_df) == 0) {
  stop("No rows available for empirical size-selection summary figure", call. = FALSE)
}

observed_dataset_labels <- unique(plot_df$dataset)
dataset_levels <- c(
  known_dataset_labels[known_dataset_labels %in% observed_dataset_labels],
  setdiff(observed_dataset_labels, known_dataset_labels)
)
plot_df <- plot_df |>
  mutate(dataset = factor(dataset, levels = dataset_levels))

# Panel A: distributional fit across models.
panel_a_df <- plot_df |>
  arrange(library_id, model_family)

# Panel B: observed in-window fraction compared with hard and best weighted predictions.
observed_df <- plot_df |>
  group_by(library_id, dataset) |>
  summarise(
    fraction = first(obs_in_window_fraction[is.finite(obs_in_window_fraction)]),
    .groups = "drop"
  ) |>
  mutate(source = "Observed reads")

hard_df <- plot_df |>
  filter(model == "hard") |>
  transmute(library_id, dataset, fraction = pred_in_window_fraction, source = "Hard window")

best_weighted_df <- plot_df |>
  filter(!model %in% c("none", "hard")) |>
  group_by(library_id, dataset) |>
  slice_min(order_by = js_read, n = 1, with_ties = FALSE) |>
  ungroup() |>
  transmute(library_id, dataset, fraction = pred_in_window_fraction, source = "Best weighted")

panel_b_df <- bind_rows(observed_df, hard_df, best_weighted_df) |>
  filter(is.finite(fraction)) |>
  mutate(
    source = factor(
      source,
      levels = c("Observed reads", "Hard window", "Best weighted")
    )
  )

SEABORN <- c(
  blue = "#4C72B0",
  orange = "#DD8452",
  green = "#55A868",
  red = "#C44E52",
  purple = "#8172B3",
  gray = "#8C8C8C",
  dark_gray = "#4D4D4D"
)

dataset_levels <- levels(droplevels(plot_df$dataset))
dataset_palette <- rep(
  c(SEABORN["blue"], SEABORN["orange"], SEABORN["green"], SEABORN["purple"], SEABORN["red"]),
  length.out = length(dataset_levels)
)
dataset_palette <- setNames(dataset_palette, dataset_levels)

p_js <- ggplot(panel_a_df, aes(x = model_family, y = js_read, group = dataset, color = dataset)) +
  geom_line(linewidth = 0.45, alpha = 0.85) +
  geom_point(size = 2.0) +
  scale_color_manual(values = dataset_palette, drop = FALSE) +
  scale_y_continuous(
    labels = label_number(accuracy = 0.01),
    expand = expansion(mult = c(0.02, 0.08))
  ) +
  labs(
    x = NULL,
    y = "Jensen-Shannon distance",
    color = "Dataset"
  ) +
  theme_minimal(base_size = 9) +
  theme(
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_blank(),
    axis.text.x = element_text(angle = 28, hjust = 1),
    legend.position = "bottom",
    plot.margin = margin(t = 4, r = 8, b = 4, l = 4)
  )

p_window <- ggplot(panel_b_df, aes(x = source, y = fraction, fill = dataset)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.64) +
  scale_fill_manual(values = dataset_palette, drop = FALSE) +
  scale_y_continuous(
    labels = label_percent(accuracy = 1),
    limits = c(0, 1),
    expand = expansion(mult = c(0, 0.04))
  ) +
  labs(
    x = NULL,
    y = "Fraction inside nominal window",
    fill = "Dataset"
  ) +
  theme_minimal(base_size = 9) +
  theme(
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_blank(),
    axis.text.x = element_text(angle = 18, hjust = 1),
    legend.position = "none",
    plot.margin = margin(t = 4, r = 8, b = 4, l = 4)
  )

p <- p_js / p_window +
  plot_annotation(tag_levels = "A") &
  theme(plot.tag = element_text(face = "bold"))

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
    ggsave(output, plot = p, width = 7.4, height = 6.2, device = cairo_pdf)
  } else {
    ggsave(output, plot = p, width = 7.4, height = 6.2)
  }
}
