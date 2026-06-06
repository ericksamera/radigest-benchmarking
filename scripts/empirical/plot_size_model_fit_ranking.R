#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(readr)
  library(scales)
  library(stringr)
})

args <- commandArgs(trailingOnly = TRUE)

arg_values <- function(flag, default = NULL) {
  idx <- match(flag, args)
  if (is.na(idx)) {
    return(default)
  }
  start <- idx + 1
  if (start > length(args) || startsWith(args[[start]], "--")) {
    stop("Missing value for ", flag, call. = FALSE)
  }
  next_flags <- which(seq_along(args) > idx & startsWith(args, "--"))
  end <- if (length(next_flags) == 0) length(args) else min(next_flags) - 1
  args[start:end]
}

arg_value <- function(flag, default = NULL) {
  values <- arg_values(flag, default = default)
  if (is.null(values)) {
    return(NULL)
  }
  values[[1]]
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

curve_paths <- arg_values("--curves")
out_table <- arg_value("--out-table")
out_figure <- arg_value("--out-figure")
formats <- str_split(arg_value("--formats", "pdf"), ",", simplify = TRUE) |>
  as.character() |>
  str_trim()
formats <- formats[formats != ""]

if (is.null(curve_paths) || length(curve_paths) == 0) {
  stop("--curves is required", call. = FALSE)
}
if (is.null(out_table)) {
  stop("--out-table is required", call. = FALSE)
}
if (is.null(out_figure)) {
  stop("--out-figure is required", call. = FALSE)
}

curves <- bind_rows(lapply(curve_paths, function(path) {
  read_tsv(path, show_col_types = FALSE, progress = FALSE) |>
    mutate(source_path = path)
}))

required_columns <- c(
  "library_id", "display_name", "model", "model_label", "model_params",
  "length", "empirical_density", "pred_weighted_density",
  "min_size", "max_size", "score_min", "score_max",
  "length_bias_beta_per_bp"
)
missing_columns <- setdiff(required_columns, names(curves))
if (length(missing_columns) > 0) {
  stop("Missing columns in curves table(s): ", paste(missing_columns, collapse = ", "), call. = FALSE)
}

model_order <- c(
  "none", "hard", "soft-window", "soft-window-short-bias", "normal", "triangular"
)

ranking <- curves |>
  mutate(
    model = factor(model, levels = model_order),
    length = as.integer(length),
    empirical_density = as.numeric(empirical_density),
    pred_weighted_density = as.numeric(pred_weighted_density),
    min_size = as.numeric(min_size),
    max_size = as.numeric(max_size),
    score_min = as.numeric(score_min),
    score_max = as.numeric(score_max),
    length_bias_beta_per_bp = as.numeric(length_bias_beta_per_bp)
  ) |>
  filter(!is.na(model), length >= score_min, length <= score_max) |>
  group_by(library_id, display_name, model, model_label, model_params) |>
  summarise(
    min_size = first(min_size),
    max_size = first(max_size),
    score_min = first(score_min),
    score_max = first(score_max),
    size_edge_sd = first(as.numeric(size_edge_sd)),
    length_bias_beta_per_bp = first(length_bias_beta_per_bp),
    js_read = jensen_shannon_distance(pred_weighted_density, empirical_density),
    pred_median = weighted_median(length, pred_weighted_density),
    obs_median = weighted_median(length, empirical_density),
    pred_in_window_fraction = {
      total <- sum(pred_weighted_density)
      if (total <= 0) NA_real_ else sum(pred_weighted_density[length >= first(min_size) & length <= first(max_size)]) / total
    },
    obs_in_window_fraction = {
      total <- sum(empirical_density)
      if (total <= 0) NA_real_ else sum(empirical_density[length >= first(min_size) & length <= first(max_size)]) / total
    },
    .groups = "drop"
  ) |>
  mutate(
    model = as.character(model),
    model_family = model_family_label(model),
    model_family = factor(
      model_family,
      levels = c(
        "Raw digest", "Hard window", "Soft window", "Soft + short-bias",
        "Normal", "Triangular"
      )
    )
  ) |>
  arrange(library_id, js_read) |>
  group_by(library_id) |>
  mutate(
    rank = row_number(),
    y_label = paste0(rank, ". ", as.character(model_family)),
    y_key = paste(library_id, sprintf("%02d", rank), as.character(model_family), sep = "||"),
    js_label = sprintf("%.3f", js_read),
    beta_label = if_else(
      model == "soft-window-short-bias" & is.finite(length_bias_beta_per_bp),
      paste0("beta=", format(length_bias_beta_per_bp, trim = TRUE, scientific = FALSE), "/bp"),
      ""
    )
  ) |>
  ungroup()

out_table <- as.character(out_table)
dir.create(dirname(out_table), recursive = TRUE, showWarnings = FALSE)
write_tsv(
  ranking |>
    select(
      library_id, display_name, rank, model, model_family, model_label, model_params,
      min_size, max_size, score_min, score_max, size_edge_sd,
      length_bias_beta_per_bp, js_read, pred_median, obs_median,
      pred_in_window_fraction, obs_in_window_fraction
    ),
  out_table
)

if (nrow(ranking) == 0) {
  stop("No model ranking rows produced", call. = FALSE)
}

label_lookup <- ranking |>
  select(y_key, y_label) |>
  distinct()
y_levels <- ranking |>
  arrange(library_id, desc(rank)) |>
  pull(y_key) |>
  unique()
y_labels <- setNames(label_lookup$y_label, label_lookup$y_key)
xmax <- max(ranking$js_read, na.rm = TRUE) * 1.18
if (!is.finite(xmax) || xmax <= 0) {
  xmax <- 1
}
dataset_count <- n_distinct(ranking$display_name)
facet_cols <- min(2, dataset_count)
facet_rows <- ceiling(dataset_count / facet_cols)
models_per_dataset <- ranking |>
  count(library_id, name = "n_models") |>
  pull(n_models)
height <- max(4.0, 2.3 + 0.42 * max(models_per_dataset, na.rm = TRUE) * facet_rows)
width <- if (facet_cols > 1) 9.2 else 7.2

p <- ggplot(ranking, aes(x = js_read, y = factor(y_key, levels = y_levels))) +
  geom_col(width = 0.68, fill = "grey55") +
  geom_text(aes(label = js_label), hjust = -0.15, size = 2.8) +
  facet_wrap(vars(display_name), ncol = facet_cols, scales = "free_y") +
  scale_y_discrete(labels = y_labels) +
  scale_x_continuous(
    labels = label_number(accuracy = 0.001),
    expand = expansion(mult = c(0, 0.02))
  ) +
  coord_cartesian(xlim = c(0, xmax), clip = "off") +
  labs(
    title = "Soft recovery models better match empirical insert-size distributions",
    subtitle = "Lower Jensen-Shannon distance indicates better agreement with empirical read-pair TLEN density",
    x = "Jensen-Shannon distance",
    y = NULL,
    caption = "Models are ranked independently within each empirical library. Short-bias is the best beta from the configured beta grid; model parameters are written to the accompanying TSV."
  ) +
  theme_minimal(base_size = 9) +
  theme(
    plot.title = element_text(face = "bold"),
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    strip.text = element_text(face = "bold", hjust = 0),
    plot.caption = element_text(hjust = 0, color = "grey35", size = 8),
    plot.caption.position = "plot",
    plot.margin = margin(t = 8, r = 18, b = 8, l = 8)
  )

base_stem <- tools::file_path_sans_ext(out_figure)
out_ext <- tools::file_ext(out_figure)
if (identical(out_ext, "")) {
  requested_outputs <- file.path(dirname(out_figure), paste0(basename(out_figure), ".", formats))
} else if (length(formats) == 1 && identical(tolower(out_ext), tolower(formats[[1]]))) {
  requested_outputs <- out_figure
} else {
  requested_outputs <- paste0(base_stem, ".", formats)
}

for (output in requested_outputs) {
  dir.create(dirname(output), recursive = TRUE, showWarnings = FALSE)
  fmt <- tolower(tools::file_ext(output))
  if (identical(fmt, "pdf") && isTRUE(capabilities("cairo"))) {
    ggsave(output, plot = p, width = width, height = height, device = cairo_pdf)
  } else {
    ggsave(output, plot = p, width = width, height = height)
  }
}
