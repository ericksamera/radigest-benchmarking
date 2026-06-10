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
    TRUE ~ str_wrap(display_name, width = 16)
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
    model_family = model_family_label(model),
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

# Panel A: distributional agreement across model families. Lower JS distance is better.
panel_a_df <- plot_df |>
  mutate(
    model_family = factor(model_family, levels = model_order),
    js_label = sprintf("%.3f", js_read)
  ) |>
  filter(!is.na(model_family))

# Panel B: how much the predicted in-window fraction differs from observed reads.
hard_df <- plot_df |>
  filter(model == "hard") |>
  transmute(
    library_id,
    dataset,
    source = "Hard window",
    predicted = pred_in_window_fraction,
    observed = obs_in_window_fraction,
    model_family = as.character(model_family)
  )

best_weighted_df <- plot_df |>
  filter(!model %in% c("none", "hard")) |>
  group_by(library_id, dataset) |>
  slice_min(order_by = js_read, n = 1, with_ties = FALSE) |>
  ungroup() |>
  transmute(
    library_id,
    dataset,
    source = "Best weighted",
    predicted = pred_in_window_fraction,
    observed = obs_in_window_fraction,
    model_family = as.character(model_family)
  )

panel_b_df <- bind_rows(hard_df, best_weighted_df) |>
  filter(is.finite(predicted), is.finite(observed)) |>
  mutate(
    error_pp = 100 * (predicted - observed),
    source = factor(source, levels = c("Hard window", "Best weighted"))
  )

if (nrow(panel_b_df) == 0) {
  stop("No in-window prediction rows available for Panel B", call. = FALSE)
}

p_js <- ggplot(panel_a_df, aes(x = model_family, y = dataset, fill = js_read)) +
  geom_tile(color = "white", linewidth = 0.6) +
  geom_text(aes(label = js_label, color = js_read > 0.72), size = 2.7) +
  scale_color_manual(values = c(`FALSE` = "black", `TRUE` = "white"), guide = "none") +
  scale_fill_gradient(
    low = "grey96",
    high = "grey35",
    labels = label_number(accuracy = 0.01),
    name = "JS distance\n(lower better)"
  ) +
  labs(x = NULL, y = NULL) +
  theme_minimal(base_size = 9) +
  theme(
    panel.grid = element_blank(),
    axis.text.x = element_text(angle = 28, hjust = 1),
    legend.position = "right",
    plot.margin = margin(t = 4, r = 8, b = 4, l = 4)
  )

point_position <- position_dodge(width = 0.45)
y_min <- min(0, panel_b_df$error_pp, na.rm = TRUE)
y_max <- max(0, panel_b_df$error_pp, na.rm = TRUE)
y_pad <- max(5, 0.08 * (y_max - y_min))

p_window <- ggplot(panel_b_df, aes(x = dataset, y = error_pp, shape = source)) +
  geom_hline(yintercept = 0, linetype = "dashed", linewidth = 0.35, color = "grey45") +
  geom_point(position = point_position, size = 2.4) +
  scale_shape_manual(values = c("Hard window" = 16, "Best weighted" = 17)) +
  scale_y_continuous(
    labels = label_number(accuracy = 1, suffix = " pp"),
    limits = c(y_min - y_pad, y_max + y_pad),
    expand = expansion(mult = c(0, 0.02))
  ) +
  labs(
    x = NULL,
    y = "Predicted - observed\nin-window fraction",
    shape = NULL
  ) +
  theme_minimal(base_size = 9) +
  theme(
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_blank(),
    legend.position = "bottom",
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
    ggsave(output, plot = p, width = 7.4, height = 5.6, device = cairo_pdf)
  } else {
    ggsave(output, plot = p, width = 7.4, height = 5.6)
  }
}
