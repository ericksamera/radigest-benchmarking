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
    model %in% c("soft-window-short-bias", "protocol-prior") ~ "Protocol prior",
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

theme_radigest <- function(base_size = 9) {
  theme_minimal(base_size = base_size) +
    theme(
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(color = "#D8DCE3", linewidth = 0.35),
      axis.title = element_text(color = "#2F2F2F"),
      axis.text = element_text(color = "#3A3A3A"),
      legend.title = element_text(color = "#2F2F2F"),
      legend.text = element_text(color = "#3A3A3A"),
      plot.tag = element_text(face = "bold", size = rel(1.45), color = "#1F1F1F"),
      plot.margin = margin(t = 5, r = 8, b = 5, l = 6)
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

model_order <- c(
  "Raw digest", "Hard window", "Soft window", "Protocol prior",
  "Normal", "Triangular"
)

# Keep the most interpretable empirical examples in a stable visual order. ggplot
# renders factor levels from bottom to top on a discrete y-axis, so this order
# places Rhododendron at the top and Sockeye at the bottom.
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

# Panel B: dumbbell plot of in-window prediction error. Values closer to zero
# indicate that the predicted in-window fraction better matches empirical reads.
hard_df <- plot_df |>
  filter(model == "hard") |>
  transmute(
    library_id,
    dataset,
    hard_error_pp = 100 * (pred_in_window_fraction - obs_in_window_fraction)
  )

best_weighted_df <- plot_df |>
  filter(!model %in% c("none", "hard")) |>
  group_by(library_id, dataset) |>
  slice_min(order_by = js_read, n = 1, with_ties = FALSE) |>
  ungroup() |>
  transmute(
    library_id,
    dataset,
    best_weighted_error_pp = 100 * (pred_in_window_fraction - obs_in_window_fraction),
    best_weighted_model = as.character(model_family)
  )

panel_b_segments <- hard_df |>
  inner_join(best_weighted_df, by = c("library_id", "dataset")) |>
  filter(is.finite(hard_error_pp), is.finite(best_weighted_error_pp))

if (nrow(panel_b_segments) == 0) {
  stop("No in-window prediction rows available for Panel B", call. = FALSE)
}

panel_b_points <- bind_rows(
  panel_b_segments |>
    transmute(dataset, source = "Hard window", error_pp = hard_error_pp),
  panel_b_segments |>
    transmute(dataset, source = "Best weighted", error_pp = best_weighted_error_pp)
) |>
  mutate(source = factor(source, levels = c("Hard window", "Best weighted")))

x_min <- min(0, panel_b_points$error_pp, na.rm = TRUE)
x_max <- max(0, panel_b_points$error_pp, na.rm = TRUE)
x_pad <- max(4, 0.08 * (x_max - x_min))

col_hard <- "#DD8452"
col_best <- "#4C72B0"
col_segment <- "#BFC5CF"

js_upper <- max(0.85, max(panel_a_df$js_read, na.rm = TRUE))
js_mid <- min(0.45, js_upper / 2)

p_js <- ggplot(panel_a_df, aes(x = model_family, y = dataset, fill = js_read)) +
  geom_tile(color = "white", linewidth = 1.0) +
  geom_text(aes(label = js_label, color = js_read <= 0.14 | js_read >= 0.68), size = 3.05) +
  scale_color_manual(values = c(`FALSE` = "#202020", `TRUE` = "white"), guide = "none") +
  scale_fill_gradient2(
    low = "#4C72B0",
    mid = "#F7F7F7",
    high = "#DD8452",
    midpoint = js_mid,
    limits = c(0, js_upper),
    oob = squish,
    breaks = seq(0, 0.8, by = 0.2),
    labels = label_number(accuracy = 0.01),
    name = "JS distance\nblue = better\norange = worse"
  ) +
  labs(x = NULL, y = NULL) +
  theme_radigest(base_size = 9) +
  theme(
    panel.grid = element_blank(),
    axis.text.x = element_text(angle = 28, hjust = 1),
    legend.position = "right",
    legend.key.height = unit(0.55, "cm")
  )

p_window <- ggplot(panel_b_segments, aes(y = dataset)) +
  geom_vline(xintercept = 0, linetype = "dashed", linewidth = 0.45, color = "#7A7A7A") +
  geom_segment(
    aes(x = best_weighted_error_pp, xend = hard_error_pp, yend = dataset),
    color = col_segment,
    linewidth = 1.25,
    lineend = "round"
  ) +
  geom_point(
    data = panel_b_points,
    aes(x = error_pp, shape = source, color = source),
    size = 3.0,
    stroke = 0.25
  ) +
  scale_shape_manual(values = c("Hard window" = 16, "Best weighted" = 17), name = NULL) +
  scale_color_manual(values = c("Hard window" = col_hard, "Best weighted" = col_best), name = NULL) +
  scale_x_continuous(
    labels = function(x) paste0(round(x), " pp"),
    limits = c(x_min - x_pad, x_max + x_pad),
    expand = expansion(mult = c(0, 0.02))
  ) +
  labs(
    x = "Prediction error in in-window fraction\n(predicted - observed, percentage points)",
    y = NULL
  ) +
  theme_radigest(base_size = 9) +
  theme(
    panel.grid.major.y = element_blank(),
    legend.position = "bottom"
  )

p <- p_js / p_window +
  plot_annotation(tag_levels = "A") +
  plot_layout(heights = c(1.0, 0.9)) &
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
