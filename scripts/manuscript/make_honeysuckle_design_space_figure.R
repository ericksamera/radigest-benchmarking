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

region_df <- plot_df |>
  distinct(target_label, target_pct, tolerance_pct, depth_target) |>
  mutate(
    xmin = target_pct - tolerance_pct,
    xmax = target_pct + tolerance_pct,
    ymin = depth_target,
    ymax = Inf
  )

x_min <- min(plot_df$recovered_genome_pct, na.rm = TRUE)
x_max <- max(plot_df$recovered_genome_pct, na.rm = TRUE)
y_max <- max(plot_df$expected_mean_depth, region_df$depth_target * 1.7, na.rm = TRUE)

depth_breaks <- c(0, 10, 30, 60, 100, 300, 1000, 3000, 10000, 30000, 100000)
depth_breaks <- depth_breaks[depth_breaks <= (y_max * 1.1)]
if (!60 %in% depth_breaks) {
  depth_breaks <- sort(unique(c(depth_breaks, 60)))
}

annotation_df <- region_df |>
  mutate(
    feasible_x = target_pct,
    feasible_y = pmax(depth_target * 3.0, 140),
    too_narrow_x = pmax(x_min + 0.45, xmin - tolerance_pct * 0.8),
    too_narrow_y = pmax(depth_target / 1.8, 18),
    too_broad_x = pmin(x_max - 1.0, xmax + tolerance_pct * 6),
    too_broad_y = pmax(depth_target / 1.8, 18)
  )

base_theme <- function(base_size = 9.5) {
  theme_minimal(base_size = base_size, base_family = "Helvetica") +
    theme(
      panel.background = element_rect(fill = "#EAEAF2", color = NA),
      plot.background = element_rect(fill = "white", color = NA),
      panel.grid.major = element_line(color = "white", linewidth = 0.35),
      panel.grid.minor = element_blank(),
      strip.background = element_rect(fill = "#D8D8E4", color = NA),
      strip.text = element_text(face = "bold", size = base_size + 0.8, color = "#2F2F2F"),
      axis.title = element_text(size = base_size + 1, color = "#2F2F2F"),
      axis.text = element_text(size = base_size, color = "#2F2F2F"),
      legend.position = "top",
      legend.title = element_blank(),
      legend.key.height = grid::unit(0.35, "lines"),
      plot.title = element_blank(),
      plot.margin = margin(6, 12, 6, 6)
    )
}

p <- ggplot(plot_df, aes(x = recovered_genome_pct, y = expected_mean_depth)) +
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
    data = filter(plot_df, !feasible),
    color = SEABORN[["gray"]],
    alpha = 0.58,
    size = 1.45
  ) +
  geom_point(
    data = filter(plot_df, feasible),
    aes(fill = feasibility),
    shape = 21,
    color = "white",
    stroke = 0.3,
    size = 2.7
  ) +
  geom_text(
    data = annotation_df,
    aes(x = feasible_x, y = feasible_y, label = "feasible\nregion"),
    inherit.aes = FALSE,
    size = 2.8,
    lineheight = 0.92,
    color = SEABORN[["green"]],
    fontface = "bold"
  ) +
  geom_text(
    data = annotation_df,
    aes(x = too_narrow_x, y = too_narrow_y, label = "too narrow"),
    inherit.aes = FALSE,
    size = 2.6,
    color = SEABORN[["dark_gray"]]
  ) +
  geom_text(
    data = annotation_df,
    aes(x = too_broad_x, y = too_broad_y, label = "too broad"),
    inherit.aes = FALSE,
    size = 2.6,
    color = SEABORN[["dark_gray"]]
  ) +
  facet_wrap(~target_label, nrow = 1) +
  scale_fill_manual(values = c(Feasible = SEABORN[["blue"]])) +
  scale_x_continuous(
    name = "Predicted weighted genome recovery (%)",
    labels = label_number(accuracy = 0.1),
    expand = expansion(mult = c(0.04, 0.08))
  ) +
  scale_y_continuous(
    name = "Expected mean read-pair depth per locus (×; pseudo-log scale)",
    trans = pseudo_log_trans(base = 10, sigma = 1),
    breaks = depth_breaks,
    labels = label_comma(accuracy = 1),
    limits = c(0, y_max * 1.08),
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
    height = 4.6,
    units = "in",
    device = grDevices::cairo_pdf,
    limitsize = FALSE
  )
} else {
  ggsave(
    out_path,
    plot = p,
    width = 7.8,
    height = 4.6,
    units = "in",
    dpi = 300,
    limitsize = FALSE
  )
}

message("Wrote ", out_path)
