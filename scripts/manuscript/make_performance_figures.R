#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(forcats)
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

input_format_path <- arg_value("--input-format")
screening_speed_path <- arg_value("--screening-speed")
thread_scaling_path <- arg_value("--thread-scaling")
pair_screen_path <- arg_value("--pair-screen-scaling")
large_genome_path <- arg_value("--large-genome")
matched_timing_path <- arg_value("--matched-timing")
out_dir <- arg_value("--out-dir", "results/manuscript/figures")
formats <- str_split(arg_value("--formats", "pdf"), ",", simplify = TRUE) |>
  as.character() |>
  str_trim()
formats <- formats[formats != ""]

if (!dir.exists(out_dir)) {
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
}

read_table <- function(path) {
  if (is.null(path) || !file.exists(path)) {
    return(NULL)
  }
  read_tsv(path, show_col_types = FALSE, progress = FALSE)
}

write_plot <- function(plot, stem, width = 7.0, height = 4.5) {
  for (fmt in formats) {
    output <- file.path(out_dir, paste0(stem, ".", fmt))
    ggsave(output, plot = plot, width = width, height = height, units = "in")
    message("Wrote ", output)
  }
}

base_theme <- function() {
  theme_minimal(base_size = 10) +
    theme(
      panel.grid.minor = element_blank(),
      plot.title.position = "plot",
      legend.position = "bottom",
      strip.text = element_text(face = "bold")
    )
}

safe_numeric <- function(x) suppressWarnings(as.numeric(x))

plot_input_format <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  df <- df |>
    mutate(
      median_wall_seconds = safe_numeric(median_wall_seconds),
      input_format = fct_reorder(input_format, median_wall_seconds)
    )
  p <- ggplot(df, aes(x = input_format, y = median_wall_seconds)) +
    geom_col(width = 0.65) +
    geom_text(aes(label = number(median_wall_seconds, accuracy = 0.01)),
              vjust = -0.25, size = 3) +
    facet_wrap(vars(condition_id), scales = "free_y") +
    labs(
      title = "radigest input-format timing",
      x = "Input format",
      y = "Median wall time (s)",
      caption = "Rows with non-PASS status should be treated as failed figure inputs."
    ) +
    base_theme()
  write_plot(p, "figure_06_input_format", width = 6.0, height = 4.0)
}

plot_screening_speed <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  df <- df |>
    mutate(
      candidate_pairs_per_second_median = safe_numeric(candidate_pairs_per_second_median),
      case_id = fct_reorder(case_id, candidate_pairs_per_second_median)
    )
  p <- ggplot(df, aes(x = case_id, y = candidate_pairs_per_second_median)) +
    geom_col(width = 0.65) +
    coord_flip() +
    labs(
      title = "Cached pair-screening throughput",
      x = NULL,
      y = "Median candidate pairs / second"
    ) +
    base_theme()
  write_plot(p, "figure_05_screening_speed", width = 7.0, height = 3.8)
}

plot_thread_scaling <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  df <- df |>
    mutate(
      threads = safe_numeric(threads),
      speedup_vs_1_thread_median = safe_numeric(speedup_vs_1_thread_median),
      output_mode = str_replace_all(output_mode, "_", " ")
    )
  p <- ggplot(df, aes(x = threads, y = speedup_vs_1_thread_median, group = output_mode)) +
    geom_abline(slope = 1, intercept = 0, linetype = "dashed", linewidth = 0.3) +
    geom_line() +
    geom_point(size = 2) +
    facet_grid(condition_id ~ output_mode) +
    scale_x_continuous(breaks = sort(unique(df$threads))) +
    labs(
      title = "Intra-tool radigest thread scaling",
      x = "Threads",
      y = "Median speedup vs. 1 thread"
    ) +
    base_theme()
  write_plot(p, "figure_s02_thread_scaling", width = 7.0, height = 4.5)
}

plot_pair_screen_scaling <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  df <- df |>
    mutate(
      jobs = safe_numeric(jobs),
      speedup_vs_1_job_median = safe_numeric(speedup_vs_1_job_median),
      job_scaling_efficiency_vs_1_job = safe_numeric(job_scaling_efficiency_vs_1_job)
    )
  p <- ggplot(df, aes(x = jobs, y = speedup_vs_1_job_median)) +
    geom_abline(slope = 1, intercept = 0, linetype = "dashed", linewidth = 0.3) +
    geom_line() +
    geom_point(size = 2) +
    scale_x_continuous(breaks = sort(unique(df$jobs))) +
    labs(
      title = "Cached pair-screen job scaling",
      x = "Screening jobs",
      y = "Median speedup vs. 1 job"
    ) +
    base_theme()
  write_plot(p, "figure_s03_pair_screen_job_scaling", width = 6.0, height = 4.0)
}

plot_large_genome <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  df <- df |>
    mutate(
      median_wall_seconds = safe_numeric(median_wall_seconds),
      output_mode = str_replace_all(output_mode, "_", " "),
      dataset_id = fct_reorder(dataset_id, median_wall_seconds)
    )
  p <- ggplot(df, aes(x = dataset_id, y = median_wall_seconds)) +
    geom_col(width = 0.65) +
    coord_flip() +
    facet_wrap(vars(output_mode), scales = "free_y") +
    labs(
      title = "Large-reference radigest timing",
      x = NULL,
      y = "Median wall time (s)"
    ) +
    base_theme()
  write_plot(p, "figure_s04_large_genome", width = 7.0, height = 4.0)
}

plot_matched_timing <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  df <- df |>
    mutate(
      median_wall_seconds = safe_numeric(median_wall_seconds),
      relative_to_radigest_median = safe_numeric(relative_to_radigest_median),
      tool = fct_reorder(tool, median_wall_seconds)
    )
  p <- ggplot(df, aes(x = tool, y = median_wall_seconds)) +
    geom_col(width = 0.65) +
    coord_flip() +
    facet_grid(dataset_id ~ condition_id, scales = "free_y", space = "free_y") +
    labs(
      title = "Semantics-aware matched-tool timing",
      x = NULL,
      y = "Median wall time (s)"
    ) +
    base_theme()
  write_plot(p, "figure_04_matched_tool_timing", width = 8.0, height = 5.0)
}

plot_input_format(input_format_path)
plot_screening_speed(screening_speed_path)
plot_thread_scaling(thread_scaling_path)
plot_pair_screen_scaling(pair_screen_path)
plot_large_genome(large_genome_path)
plot_matched_timing(matched_timing_path)
