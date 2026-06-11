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

required_arg <- function(flag) {
  value <- arg_value(flag)
  if (is.null(value) || identical(value, "")) {
    stop("Missing required argument ", flag, call. = FALSE)
  }
  value
}

design_2pct_path <- required_arg("--design-2pct")
design_1p5pct_path <- required_arg("--design-1p5pct")
out_path <- required_arg("--out")
fallback_depth_target <- as.numeric(arg_value("--depth-target", "60"))
fallback_tolerance_pct <- as.numeric(arg_value("--tolerance-pct", "0.25"))

if (!dir.exists(dirname(out_path))) {
  dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
}

SEABORN <- c(
  blue = "#4C72B0",
  orange = "#DD8452",
  green = "#55A868",
  red = "#C44E52",
  gray = "#8C8C8C",
  dark_gray = "#4D4D4D"
)

first_present <- function(df, candidates, required = TRUE, label = "column") {
  hit <- candidates[candidates %in% names(df)]
  if (length(hit) > 0) {
    return(hit[[1]])
  }
  if (required) {
    stop(
      "Could not find ", label, "; tried: ",
      paste(candidates, collapse = ", "),
      call. = FALSE
    )
  }
  NA_character_
}

as_numeric_column <- function(df, candidates, label) {
  column <- first_present(df, candidates, required = TRUE, label = label)
  suppressWarnings(as.numeric(df[[column]]))
}

scalar_from_column <- function(df, candidates, fallback, label) {
  column <- first_present(df, candidates, required = FALSE, label = label)
  if (is.na(column)) {
    return(fallback)
  }
  values <- suppressWarnings(as.numeric(df[[column]]))
  values <- values[is.finite(values)]
  if (length(values) == 0) {
    return(fallback)
  }
  values[[1]]
}

truthy <- function(x) {
  str_to_lower(str_trim(as.character(x))) %in% c("true", "t", "yes", "y", "1", "pass", "feasible")
}

make_pair_label <- function(df) {
  pair_col <- first_present(
    df,
    c("enzyme_pair", "pair", "enzyme_pair_id", "pair_id"),
    required = FALSE,
    label = "enzyme-pair label"
  )
  if (!is.na(pair_col)) {
    return(str_replace_all(as.character(df[[pair_col]]), "[+,/]", "–"))
  }

  enzyme1_col <- first_present(
    df,
    c("enzyme_1", "enzyme1", "enzyme_a", "enzymeA", "enzyme_left"),
    required = TRUE,
    label = "first enzyme"
  )
  enzyme2_col <- first_present(
    df,
    c("enzyme_2", "enzyme2", "enzyme_b", "enzymeB", "enzyme_right"),
    required = TRUE,
    label = "second enzyme"
  )
  paste(df[[enzyme1_col]], df[[enzyme2_col]], sep = "–")
}

read_design <- function(path, target_label, fallback_target_pct) {
  if (!file.exists(path)) {
    stop("Missing design table: ", path, call. = FALSE)
  }
  df <- read_tsv(path, show_col_types = FALSE, progress = FALSE)
  if (nrow(df) == 0) {
    stop("No rows in design table: ", path, call. = FALSE)
  }

  target_pct <- scalar_from_column(
    df,
    c("target_genome_pct", "target_recovered_genome_pct", "target_recovery_pct"),
    fallback_target_pct,
    "target genome percentage"
  )
  tolerance_pct <- scalar_from_column(
    df,
    c("coverage_tolerance_pct", "genome_tolerance_pct", "target_tolerance_pct"),
    fallback_tolerance_pct,
    "coverage tolerance percentage"
  )
  depth_target <- scalar_from_column(
    df,
    c("target_mean_locus_depth", "target_mean_depth", "desired_depth"),
    fallback_depth_target,
    "target mean depth"
  )

  recovery <- as_numeric_column(
    df,
    c(
      "predicted_weighted_genome_pct",
      "generated_weighted_genome_pct",
      "weighted_genome_pct",
      "recovered_genome_pct",
      "genome_pct",
      "weighted_recovered_genome_pct"
    ),
    "predicted recovered-genome percentage"
  )
  depth <- as_numeric_column(
    df,
    c(
      "predicted_mean_locus_depth",
      "expected_mean_depth",
      "mean_locus_depth",
      "predicted_depth",
      "expected_depth"
    ),
    "predicted mean depth"
  )

  feasible_col <- first_present(
    df,
    c("feasible", "is_feasible", "passes", "meets_targets", "status"),
    required = FALSE,
    label = "feasibility flag"
  )
  feasible <- if (is.na(feasible_col)) {
    abs(recovery - target_pct) <= tolerance_pct & depth >= depth_target
  } else {
    truthy(df[[feasible_col]]) |
      (abs(recovery - target_pct) <= tolerance_pct & depth >= depth_target)
  }

  tibble(
    source = path,
    target_label = target_label,
    target_pct = target_pct,
    tolerance_pct = tolerance_pct,
    depth_target = depth_target,
    enzyme_pair = make_pair_label(df),
    recovered_genome_pct = recovery,
    expected_mean_depth = depth,
    feasible = feasible
  ) |>
    filter(is.finite(recovered_genome_pct), is.finite(expected_mean_depth))
}

plot_df <- bind_rows(
  read_design(design_2pct_path, "2.0% target", 2.0),
  read_design(design_1p5pct_path, "1.5% target", 1.5)
) |>
  mutate(
    target_label = factor(target_label, levels = c("2.0% target", "1.5% target")),
    feasibility = if_else(feasible, "Feasible", "Not feasible")
  )

if (nrow(plot_df) == 0) {
  stop("No usable design rows after parsing input design tables.", call. = FALSE)
}

target_meta <- plot_df |>
  distinct(target_label, target_pct, tolerance_pct, depth_target) |>
  mutate(target_label_chr = as.character(target_label))

x_global_max <- max(plot_df$recovered_genome_pct, na.rm = TRUE)
y_global_max <- max(plot_df$expected_mean_depth, na.rm = TRUE)
depth_target_max <- max(target_meta$depth_target, na.rm = TRUE)

full_x_limits <- c(0, x_global_max * 1.02)
full_y_limits <- c(0, max(y_global_max, depth_target_max * 1.7) * 1.08)
zoom_x_limits <- c(
  max(0, min(target_meta$target_pct - target_meta$tolerance_pct, na.rm = TRUE) - 0.35),
  max(target_meta$target_pct + target_meta$tolerance_pct, na.rm = TRUE) + 0.70
)
zoom_y_limits <- c(0, depth_target_max * 2.5)

depth_breaks <- c(0, 10, 30, 60, 100, 300, 1000, 3000, 10000, 30000, 100000)
depth_breaks <- depth_breaks[depth_breaks <= (full_y_limits[[2]] * 1.1)]
if (!60 %in% depth_breaks) {
  depth_breaks <- sort(unique(c(depth_breaks, 60)))
}

panel_specs <- tibble(
  target_label_chr = c("2.0% target", "1.5% target", "2.0% target", "1.5% target"),
  panel_label = c(
    "A. 2.0% target\nfull design space",
    "B. 1.5% target\nfull design space",
    "C. 2.0% target\nzoomed feasibility window",
    "D. 1.5% target\nzoomed feasibility window"
  ),
  view = c("full", "full", "zoom", "zoom"),
  xmin = c(full_x_limits[[1]], full_x_limits[[1]], zoom_x_limits[[1]], zoom_x_limits[[1]]),
  xmax = c(full_x_limits[[2]], full_x_limits[[2]], zoom_x_limits[[2]], zoom_x_limits[[2]]),
  ymin = c(full_y_limits[[1]], full_y_limits[[1]], zoom_y_limits[[1]], zoom_y_limits[[1]]),
  ymax = c(full_y_limits[[2]], full_y_limits[[2]], zoom_y_limits[[2]], zoom_y_limits[[2]])
)

panel_levels <- panel_specs$panel_label

panel_df <- bind_rows(lapply(seq_len(nrow(panel_specs)), function(i) {
  spec <- panel_specs[i, ]
  df <- plot_df[as.character(plot_df$target_label) == spec$target_label_chr[[1]], , drop = FALSE]

  if (spec$view[[1]] == "zoom") {
    df <- df |>
      filter(
        recovered_genome_pct >= spec$xmin[[1]],
        recovered_genome_pct <= spec$xmax[[1]],
        expected_mean_depth >= spec$ymin[[1]],
        expected_mean_depth <= spec$ymax[[1]]
      )
  }

  df |>
    mutate(
      panel_label = factor(spec$panel_label[[1]], levels = panel_levels),
      view = spec$view[[1]]
    )
}))

region_df <- bind_rows(lapply(seq_len(nrow(panel_specs)), function(i) {
  spec <- panel_specs[i, ]
  meta <- target_meta[target_meta$target_label_chr == spec$target_label_chr[[1]], , drop = FALSE]
  meta <- meta[1, , drop = FALSE]

  tibble(
    panel_label = factor(spec$panel_label[[1]], levels = panel_levels),
    view = spec$view[[1]],
    target_pct = meta$target_pct,
    tolerance_pct = meta$tolerance_pct,
    depth_target = meta$depth_target,
    xmin = meta$target_pct - meta$tolerance_pct,
    xmax = meta$target_pct + meta$tolerance_pct,
    ymin = meta$depth_target,
    ymax = spec$ymax[[1]]
  )
}))

range_df <- bind_rows(lapply(seq_len(nrow(panel_specs)), function(i) {
  spec <- panel_specs[i, ]
  tibble(
    panel_label = factor(spec$panel_label[[1]], levels = panel_levels),
    x = c(spec$xmin[[1]], spec$xmax[[1]]),
    y = c(spec$ymin[[1]], spec$ymax[[1]])
  )
}))

annotation_df <- region_df |>
  filter(view == "zoom") |>
  mutate(
    label_x = target_pct,
    label_y = pmin(ymax * 0.82, depth_target * 1.7)
  )

base_theme <- function(base_size = 9.5) {
  theme_minimal(base_size = base_size, base_family = "Helvetica") +
    theme(
      panel.background = element_rect(fill = "#EAEAF2", color = NA),
      plot.background = element_rect(fill = "white", color = NA),
      panel.grid.major = element_line(color = "white", linewidth = 0.35),
      panel.grid.minor = element_blank(),
      strip.background = element_rect(fill = "#D8D8E4", color = NA),
      strip.text = element_text(face = "bold", size = base_size, color = "#2F2F2F"),
      axis.title = element_text(size = base_size + 1, color = "#2F2F2F"),
      axis.text = element_text(size = base_size, color = "#2F2F2F"),
      legend.position = "top",
      legend.title = element_blank(),
      legend.key.height = grid::unit(0.35, "lines"),
      plot.title = element_blank(),
      plot.margin = margin(6, 12, 6, 6)
    )
}

p <- ggplot(panel_df, aes(x = recovered_genome_pct, y = expected_mean_depth)) +
  geom_blank(
    data = range_df,
    aes(x = x, y = y),
    inherit.aes = FALSE
  ) +
  geom_rect(
    data = region_df,
    aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax),
    inherit.aes = FALSE,
    fill = SEABORN[["green"]],
    alpha = 0.14
  ) +
  geom_hline(
    data = region_df,
    aes(yintercept = depth_target),
    linewidth = 0.45,
    linetype = "dashed",
    color = SEABORN[["dark_gray"]]
  ) +
  geom_vline(
    data = region_df,
    aes(xintercept = target_pct),
    linewidth = 0.35,
    linetype = "dotted",
    color = SEABORN[["dark_gray"]]
  ) +
  geom_point(
    data = filter(panel_df, !feasible),
    color = SEABORN[["gray"]],
    alpha = 0.58,
    size = 1.45
  ) +
  geom_point(
    data = filter(panel_df, feasible),
    aes(fill = feasibility),
    shape = 21,
    color = "white",
    stroke = 0.3,
    size = 2.7
  ) +
  geom_text(
    data = annotation_df,
    aes(x = label_x, y = label_y, label = "feasible\nregion"),
    inherit.aes = FALSE,
    size = 2.8,
    lineheight = 0.92,
    color = SEABORN[["green"]],
    fontface = "bold"
  ) +
  facet_wrap(~panel_label, ncol = 2, scales = "free") +
  scale_fill_manual(values = c(Feasible = SEABORN[["blue"]])) +
  scale_x_continuous(
    name = "Predicted weighted genome recovery (%)",
    labels = label_number(accuracy = 0.1),
    expand = expansion(mult = c(0.02, 0.05))
  ) +
  scale_y_continuous(
    name = "Expected mean read-pair depth per locus (×; pseudo-log scale)",
    trans = pseudo_log_trans(base = 10, sigma = 1),
    breaks = depth_breaks,
    labels = label_comma(accuracy = 1),
    minor_breaks = NULL,
    expand = expansion(mult = c(0.02, 0.08))
  ) +
  coord_cartesian(clip = "off") +
  base_theme()

if (identical(tolower(tools::file_ext(out_path)), "pdf") && isTRUE(capabilities("cairo"))) {
  ggsave(
    out_path,
    plot = p,
    width = 7.8,
    height = 7.4,
    units = "in",
    device = grDevices::cairo_pdf,
    limitsize = FALSE
  )
} else {
  ggsave(
    out_path,
    plot = p,
    width = 7.8,
    height = 7.4,
    units = "in",
    dpi = 300,
    limitsize = FALSE
  )
}

message("Wrote ", out_path)
