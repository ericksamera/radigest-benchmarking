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

weighted_median <- function(x, w) {
  ok <- is.finite(x) & is.finite(w) & w > 0
  x <- x[ok]
  w <- w[ok]
  if (length(x) == 0 || sum(w) <= 0) {
    return(NA_real_)
  }
  ord <- order(x)
  x <- x[ord]
  w <- w[ord]
  cumulative <- cumsum(w) / sum(w)
  x[[which(cumulative >= 0.5)[1]]]
}

jensen_shannon_distance <- function(p, q) {
  p <- as.numeric(p)
  q <- as.numeric(q)
  if (length(p) != length(q)) {
    stop("p and q must have the same length", call. = FALSE)
  }
  p[p < 0] <- 0
  q[q < 0] <- 0
  if (sum(p) <= 0 || sum(q) <= 0) {
    return(NA_real_)
  }
  p <- p / sum(p)
  q <- q / sum(q)
  m <- 0.5 * (p + q)
  kl_div <- function(a, b) {
    idx <- a > 0 & b > 0
    sum(a[idx] * log2(a[idx] / b[idx]))
  }
  sqrt(0.5 * kl_div(p, m) + 0.5 * kl_div(q, m))
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
  "min_size", "max_size", "score_min", "score_max",
  "length_bias_beta_per_bp"
)
missing_columns <- setdiff(required_columns, names(curves))
if (length(missing_columns) > 0) {
  stop("Missing columns in curves table: ", paste(missing_columns, collapse = ", "), call. = FALSE)
}

model_order <- c("none", "hard", "soft-window", "soft-window-short-bias", "normal", "triangular")
model_labels <- curves |>
  distinct(model, model_label) |>
  mutate(model = factor(model, levels = model_order)) |>
  arrange(model) |>
  pull(model_label)

plot_xmax <- 700
plot_df <- curves |>
  mutate(
    model = factor(model, levels = model_order),
    model_label = factor(model_label, levels = model_labels),
    length = as.integer(length),
    empirical_density = as.numeric(empirical_density),
    length_bias_beta_per_bp = as.numeric(length_bias_beta_per_bp),
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

panel_stats <- plot_df |>
  group_by(model, model_label) |>
  summarise(
    js_distance = jensen_shannon_distance(pred_weighted_density, empirical_density),
    pred_median = weighted_median(length, pred_weighted_density),
    obs_median = weighted_median(length, empirical_density),
    pred_in_window = sum(pred_weighted_density[length >= first(min_size) & length <= first(max_size)]),
    obs_in_window = sum(empirical_density[length >= first(min_size) & length <= first(max_size)]),
    .groups = "drop"
  ) |>
  mutate(
    label = sprintf(
      "JS(read) = %.3f\nMedian: pred %.0f bp | read %.0f bp\nIn window: pred %.1f%% | read %.1f%%",
      js_distance,
      pred_median,
      obs_median,
      100 * pred_in_window,
      100 * obs_in_window
    ),
    x = plot_xmax - 8,
    y = Inf
  )

plot_df_window <- plot_df |>
  filter(length <= plot_xmax)
window_df <- window_df |>
  mutate(
    xmin = pmax(min_size, 0),
    xmax = pmin(max_size, plot_xmax)
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

p <- ggplot(plot_df_window, aes(x = length)) +
  geom_rect(
    data = window_df,
    aes(xmin = xmin, xmax = xmax, ymin = -Inf, ymax = Inf),
    inherit.aes = FALSE,
    fill = "grey85",
    alpha = 0.55
  ) +
  geom_area(aes(y = pred_weighted_density), fill = "#4C72B0", alpha = 0.28) +
  geom_line(
    data = plot_df_window |> filter(model != "none"),
    aes(y = pred_raw_density),
    color = "#4D4D4D",
    linewidth = 0.35
  ) +
  geom_line(aes(y = pred_weighted_density), color = "#4C72B0", linewidth = 0.5) +
  geom_line(aes(y = empirical_density), color = "#C44E52", linewidth = 0.45) +
  geom_text(
    data = panel_stats,
    aes(x = x, y = y, label = label),
    inherit.aes = FALSE,
    hjust = 1,
    vjust = 1.05,
    size = 2.45,
    lineheight = 0.95,
    color = "grey15"
  ) +
  facet_wrap(vars(model_label), ncol = 1, scales = "free_y") +
  scale_x_continuous(
    limits = c(0, plot_xmax),
    breaks = seq(0, plot_xmax, by = 100),
    expand = expansion(mult = c(0, 0.01))
  ) +
  scale_y_continuous(
    labels = label_number(accuracy = 0.001),
    expand = expansion(mult = c(0, 0.12))
  ) +
  labs(
    x = "Insert or predicted fragment size (bp)",
    y = "Density"
  ) +
  coord_cartesian(clip = "off") +
  theme_minimal(base_size = 9) +
  theme(
    panel.grid.minor = element_blank(),
    strip.text = element_text(face = "bold", hjust = 0),
    legend.position = "none",
    axis.title.y = element_text(margin = margin(r = 6)),
    plot.margin = margin(t = 8, r = 10, b = 8, l = 8)
  )

for (output in requested_outputs) {
  dir.create(dirname(output), recursive = TRUE, showWarnings = FALSE)
  fmt <- tolower(tools::file_ext(output))
  if (identical(fmt, "pdf") && isTRUE(capabilities("cairo"))) {
    ggsave(output, plot = p, width = 7.4, height = 9.4, device = cairo_pdf)
  } else {
    ggsave(output, plot = p, width = 7.4, height = 9.4)
  }
}
