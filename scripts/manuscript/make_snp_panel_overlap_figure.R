#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(forcats)
  library(ggplot2)
  library(patchwork)
  library(readr)
  library(scales)
})

SEABORN <- c(
  blue = "#4C72B0",
  orange = "#DD8452",
  green = "#55A868",
  red = "#C44E52",
  gray = "#8C8C8C",
  dark_gray = "#4D4D4D"
)

base_theme <- function(base_size = 9) {
  theme_minimal(base_size = base_size, base_family = "Helvetica") +
    theme(
      panel.background = element_rect(fill = "#EAEAF2", color = NA),
      plot.background = element_rect(fill = "white", color = NA),
      panel.grid.major = element_line(color = "white", linewidth = 0.35),
      panel.grid.minor = element_blank(),
      panel.spacing = grid::unit(0.7, "lines"),
      axis.title = element_text(size = base_size + 1, color = "#2F2F2F"),
      axis.text = element_text(size = base_size, color = "#2F2F2F"),
      strip.background = element_rect(fill = "#D8D8E4", color = NA),
      strip.text = element_text(face = "bold", size = base_size, color = "#2F2F2F"),
      legend.position = "top",
      legend.title = element_text(color = "#2F2F2F"),
      legend.text = element_text(color = "#3A3A3A"),
      legend.key.height = grid::unit(0.35, "lines"),
      legend.spacing.x = grid::unit(0.55, "lines"),
      legend.box = "horizontal",
      plot.title = element_text(face = "bold", size = base_size + 1.2, color = "#1F1F1F"),
      plot.margin = margin(6, 10, 6, 6)
    )
}

parse_args <- function(argv) {
  out <- list()
  i <- 1
  while (i <= length(argv)) {
    key <- argv[[i]]
    if (!startsWith(key, "--")) {
      stop("unexpected positional argument: ", key, call. = FALSE)
    }
    if (i == length(argv)) {
      stop("missing value for ", key, call. = FALSE)
    }
    out[[sub("^--", "", key)]] <- argv[[i + 1]]
    i <- i + 2
  }
  out
}

require_arg <- function(args, name) {
  value <- args[[name]]
  if (is.null(value) || identical(value, "")) {
    stop("missing required argument --", name, call. = FALSE)
  }
  value
}

as_num <- function(x) suppressWarnings(as.numeric(x))

first_present <- function(df, candidates) {
  hit <- candidates[candidates %in% names(df)]
  if (length(hit) > 0) {
    return(hit[[1]])
  }
  NA_character_
}

scalar_from_column <- function(df, candidates, default = NA_real_) {
  column <- first_present(df, candidates)
  if (is.na(column)) {
    return(default)
  }
  values <- suppressWarnings(as.numeric(df[[column]]))
  values <- values[is.finite(values)]
  if (length(values) == 0) {
    return(default)
  }
  values[[1]]
}

format_depth_label <- function(x) {
  x <- as.numeric(x)
  if (!is.finite(x)) {
    return("")
  }
  if (abs(x - round(x)) < 1e-8) {
    return(as.character(round(x)))
  }
  format(round(x, 2), trim = TRUE, scientific = FALSE)
}

feasible_factor <- function(x) {
  factor(
    ifelse(
      tolower(as.character(x)) %in% c("true", "1", "yes", "pass", "feasible"),
      "Feasible",
      "Infeasible"
    ),
    levels = c("Infeasible", "Feasible")
  )
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
pairs_path <- require_arg(args, "pairs")
top_path <- require_arg(args, "top")
out_path <- require_arg(args, "out")
title <- args[["title"]]
if (is.null(title) || identical(title, "")) {
  title <- ""
}

pairs <- read_tsv(pairs_path, show_col_types = FALSE, progress = FALSE) %>%
  mutate(
    panel_loci_read_accessible = as_num(panel_loci_read_accessible),
    panel_loci_captured = as_num(panel_loci_captured),
    panel_fraction_read_accessible = as_num(panel_fraction_read_accessible),
    off_panel_fragment_bp = as_num(off_panel_fragment_bp),
    predicted_mean_locus_depth = as_num(predicted_mean_locus_depth),
    predicted_mean_locus_depth_for_size = ifelse(
      is.finite(predicted_mean_locus_depth),
      predicted_mean_locus_depth,
      0
    ),
    predicted_weighted_genome_pct = as_num(predicted_weighted_genome_pct),
    feasible = feasible_factor(feasible)
  )

# Read the top-design table to keep the input contract explicit, but build the
# bar panel from the complete pair table so high-ranking feasible designs are not
# hidden when the highest target-recovery designs are all infeasible.
top_input <- read_tsv(top_path, show_col_types = FALSE, progress = FALSE)
if (nrow(top_input) == 0) {
  stop("No rows in top-design table: ", top_path, call. = FALSE)
}
if (!("enzyme_pair" %in% names(pairs))) {
  stop("pair-overlap table must contain an enzyme_pair column", call. = FALSE)
}

top_overall <- pairs %>%
  arrange(desc(panel_loci_read_accessible), off_panel_fragment_bp, enzyme_pair) %>%
  slice_head(n = 10L)

top_feasible <- pairs %>%
  filter(as.character(feasible) == "Feasible") %>%
  arrange(desc(panel_loci_read_accessible), off_panel_fragment_bp, enzyme_pair) %>%
  slice_head(n = 5L)

top <- bind_rows(top_overall, top_feasible) %>%
  distinct(enzyme_pair, .keep_all = TRUE) %>%
  arrange(desc(panel_loci_read_accessible), off_panel_fragment_bp, enzyme_pair)

depth_target <- scalar_from_column(
  pairs,
  c("target_mean_locus_depth", "target_mean_depth", "desired_depth")
)
panel_y_max <- suppressWarnings(max(pairs$panel_loci_read_accessible, na.rm = TRUE))
if (!is.finite(panel_y_max) || panel_y_max <= 0) {
  panel_y_max <- 1
}

feasible_colors <- c(
  "Infeasible" = SEABORN[["gray"]],
  "Feasible" = SEABORN[["green"]]
)
feasible_shapes <- c(
  "Infeasible" = 16,
  "Feasible" = 17
)

p1 <- ggplot(
  pairs,
  aes(
    x = off_panel_fragment_bp / 1e6,
    y = panel_loci_read_accessible,
    color = feasible,
    shape = feasible
  )
) +
  geom_point(size = 2.35, alpha = 0.88, stroke = 0.2, na.rm = TRUE) +
  scale_color_manual(values = feasible_colors, drop = FALSE) +
  scale_shape_manual(values = feasible_shapes, drop = FALSE) +
  guides(
    color = "none",
    shape = guide_legend(
      title = "Feasibility",
      order = 1,
      override.aes = list(
        color = unname(feasible_colors),
        size = 3.1,
        alpha = 1
      )
    )
  ) +
  labs(
    x = "Off-panel hard-window burden (Mbp)",
    y = "Read-accessible panel intervals",
    color = "Feasibility",
    shape = "Feasibility",
    title = "A. Recovery versus off-panel burden"
  ) +
  base_theme()

p2 <- ggplot(
  pairs,
  aes(
    x = predicted_mean_locus_depth,
    y = panel_loci_read_accessible,
    color = feasible,
    shape = feasible
  )
) +
  geom_point(size = 2.7, alpha = 0.88, stroke = 0.2, na.rm = TRUE)

if (is.finite(depth_target)) {
  p2 <- p2 +
    geom_vline(
      xintercept = depth_target,
      linetype = "dashed",
      linewidth = 0.45,
      color = SEABORN[["orange"]],
      show.legend = FALSE
    ) +
    annotate(
      "text",
      x = depth_target,
      y = panel_y_max,
      label = paste0(format_depth_label(depth_target), "× target"),
      hjust = -0.1,
      vjust = 1.25,
      size = 2.7,
      color = SEABORN[["orange"]]
    )
}

p2 <- p2 +
  scale_color_manual(values = feasible_colors, drop = FALSE) +
  scale_shape_manual(values = feasible_shapes, drop = FALSE) +
  scale_x_continuous(
    trans = scales::pseudo_log_trans(base = 10),
    breaks = c(0, 1, 10, 100, 1000, 10000),
    labels = label_number(),
    minor_breaks = NULL
  ) +
  guides(color = "none", shape = "none") +
  labs(
    x = "Predicted mean locus depth (×; pseudo-log scale)",
    y = "Read-accessible panel intervals",
    color = "Feasibility",
    shape = "Feasibility",
    title = "B. Recovery versus expected depth"
  ) +
  base_theme()

p3 <- ggplot(
  top,
  aes(
    x = panel_loci_read_accessible,
    y = fct_reorder(enzyme_pair, panel_loci_read_accessible),
    fill = feasible
  )
) +
  geom_col(width = 0.72, show.legend = FALSE, na.rm = TRUE) +
  geom_text(
    aes(label = comma(panel_loci_read_accessible)),
    hjust = -0.1,
    size = 2.8,
    color = "#2F2F2F",
    na.rm = TRUE
  ) +
  scale_fill_manual(values = feasible_colors, drop = FALSE) +
  scale_x_continuous(
    labels = label_comma(),
    expand = expansion(mult = c(0, 0.09))
  ) +
  labs(
    x = "Read-accessible panel intervals",
    y = "Enzyme pair",
    title = "C. High-recovery pairs and feasible alternatives"
  ) +
  base_theme() +
  theme(panel.grid.major.y = element_blank())

plot <- ((p1 | p2) / p3) +
  plot_layout(guides = "collect", heights = c(1, 1.05)) &
  theme(
    legend.position = "top",
    legend.justification = "left",
    legend.box.just = "left",
    legend.margin = margin(0, 0, 2, 0)
  )

if (!is.null(title) && nzchar(trimws(title))) {
  plot <- plot +
    plot_annotation(
      title = title,
      theme = theme(
        plot.title = element_text(face = "bold", size = 12.5, color = "#1F1F1F")
      )
    )
}
dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
ggsave(out_path, plot, width = 8.8, height = 7.4, units = "in")
message("wrote ", out_path)
