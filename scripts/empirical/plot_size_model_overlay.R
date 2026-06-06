#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
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

curves_path <- arg_value("--curves")
out_path <- arg_value("--out")
formats <- str_split(arg_value("--formats", "pdf"), ",", simplify = TRUE) |>
  as.character() |>
  str_trim()
formats <- formats[formats != ""]

if (is.null(curves_path)) {
  stop("--curves is required", call. = FALSE)
}
if (is.null(out_path)) {
  stop("--out is required", call. = FALSE)
}

curves <- read_tsv(curves_path, show_col_types = FALSE, progress = FALSE)
required_columns <- c(
  "library_id", "display_name", "model", "model_label", "length",
  "empirical_density", "pred_raw_density", "pred_weighted_density",
  "min_size", "max_size", "score_min", "score_max"
)
missing_columns <- setdiff(required_columns, names(curves))
if (length(missing_columns) > 0) {
  stop("Missing columns in curves table: ", paste(missing_columns, collapse = ", "), call. = FALSE)
}

model_order <- c("none", "hard", "soft-window", "normal", "triangular")
model_labels <- curves |>
  distinct(model, model_label) |>
  mutate(model = factor(model, levels = model_order)) |>
  arrange(model) |>
  pull(model_label)

plot_df <- curves |>
  mutate(
    model = factor(model, levels = model_order),
    model_label = factor(model_label, levels = model_labels),
    length = as.integer(length),
    empirical_density = as.numeric(empirical_density),
    pred_raw_density = as.numeric(pred_raw_density),
    pred_weighted_density = as.numeric(pred_weighted_density),
    min_size = as.numeric(min_size),
    max_size = as.numeric(max_size),
    score_min = as.numeric(score_min),
    score_max = as.numeric(score_max)
  ) |>
  filter(!is.na(model), length >= score_min, length <= score_max)

if (nrow(plot_df) == 0) {
  stop("No rows to plot after filtering to score_min/score_max", call. = FALSE)
}

window_df <- plot_df |>
  distinct(model_label, min_size, max_size)

library_label <- plot_df |>
  distinct(display_name) |>
  pull(display_name) |>
  first()

base_stem <- tools::file_path_sans_ext(out_path)
out_ext <- tools::file_ext(out_path)
if (identical(out_ext, "")) {
  requested_outputs <- file.path(dirname(out_path), paste0(basename(out_path), ".", formats))
} else if (length(formats) == 1 && identical(tolower(out_ext), tolower(formats[[1]]))) {
  requested_outputs <- out_path
} else {
  requested_outputs <- paste0(base_stem, ".", formats)
}

p <- ggplot(plot_df, aes(x = length)) +
  geom_rect(
    data = window_df,
    aes(xmin = min_size, xmax = max_size, ymin = -Inf, ymax = Inf),
    inherit.aes = FALSE,
    fill = "grey85",
    alpha = 0.55
  ) +
  geom_area(aes(y = pred_weighted_density), fill = "#4C72B0", alpha = 0.28) +
  geom_line(aes(y = pred_raw_density), color = "#4D4D4D", linewidth = 0.35) +
  geom_line(aes(y = pred_weighted_density), color = "#4C72B0", linewidth = 0.45) +
  geom_line(aes(y = empirical_density), color = "#C44E52", linewidth = 0.45) +
  facet_wrap(vars(model_label), ncol = 1, scales = "free_y") +
  scale_x_continuous(expand = expansion(mult = c(0.01, 0.01))) +
  scale_y_continuous(labels = label_number(accuracy = 0.001), expand = expansion(mult = c(0, 0.08))) +
  labs(
    title = "Empirical TLENs compared with radigest size-selection models",
    subtitle = library_label,
    x = "Insert or predicted fragment size (bp)",
    y = "Proportion of fragments",
    caption = "Grey band: nominal size-selection window. Black: raw radigest fragment distribution. Blue: model-weighted prediction. Red: empirical TLEN distribution."
  ) +
  theme_minimal(base_size = 9) +
  theme(
    plot.title = element_text(face = "bold"),
    panel.grid.minor = element_blank(),
    strip.text = element_text(face = "bold", hjust = 0),
    legend.position = "none",
    plot.caption = element_text(hjust = 0, color = "grey35"),
    axis.title.y = element_text(margin = margin(r = 6))
  )

for (output in requested_outputs) {
  dir.create(dirname(output), recursive = TRUE, showWarnings = FALSE)
  fmt <- tolower(tools::file_ext(output))
  if (identical(fmt, "pdf") && isTRUE(capabilities("cairo"))) {
    ggsave(output, plot = p, width = 7.2, height = 8.4, device = cairo_pdf)
  } else {
    ggsave(output, plot = p, width = 7.2, height = 8.4)
  }
}
