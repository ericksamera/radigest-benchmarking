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

# Palette chosen to match the legible "seaborn deep" examples while keeping
# color semantic: radigest/observed data are blue, comparative/ideal/reference
# elements are muted or orange.
SEABORN <- c(
  blue = "#4C72B0",
  orange = "#DD8452",
  green = "#55A868",
  red = "#C44E52",
  purple = "#8172B3",
  gray = "#8C8C8C",
  dark_gray = "#4D4D4D"
)

DATASET_LABELS <- c(
  small_yeast_s288c_plain = "S. cerevisiae S288C",
  small_yeast_s288c_gzip = "S. cerevisiae S288C",
  `moderate_cannabis_pink-pepper_plain` = "C. sativa Pink Pepper",
  `moderate_cannabis_pink-pepper_gzip` = "C. sativa Pink Pepper",
  `large_wheat_chinese-spring_plain` = "T. aestivum Chinese Spring",
  `large_wheat_chinese-spring_gzip` = "T. aestivum Chinese Spring"
)

DATASET_ORDER <- c(
  "small_yeast_s288c_plain",
  "small_yeast_s288c_gzip",
  "moderate_cannabis_pink-pepper_plain",
  "moderate_cannabis_pink-pepper_gzip",
  "large_wheat_chinese-spring_plain",
  "large_wheat_chinese-spring_gzip"
)

CONDITION_ORDER <- c("D1", "B1", "B2")

CONDITION_LABELS <- c(
  B1 = "EcoRI-MseI, 100-300 bp",
  B2 = "EcoRI-MseI, 300-600 bp",
  D1 = "EcoRI-MseI, 1-100 bp"
)

INPUT_FORMAT_LABELS <- c(
  plain = "Plain FASTA",
  gzip = "gzip FASTA"
)

OUTPUT_MODE_LABELS <- c(
  json = "JSON summary",
  fragments_tsv = "Fragment TSV"
)

TOOL_LABELS <- c(
  radigest = "radigest",
  digital_rads = "Digital_RADs.py",
  ddradseqtools = "DDRADSEQTOOLS",
  simrad = "SimRAD",
  ddgrader = "ddgRADer"
)

TOOL_ORDER <- c(
  "radigest",
  "digital_rads",
  "ddradseqtools",
  "simrad",
  "ddgrader"
)

read_table <- function(path) {
  if (is.null(path) || !file.exists(path)) {
    return(NULL)
  }
  read_tsv(path, show_col_types = FALSE, progress = FALSE)
}

write_plot <- function(plot, stem, width = 7.0, height = 4.5) {
  for (fmt in formats) {
    output <- file.path(out_dir, paste0(stem, ".", fmt))
    fmt_lower <- tolower(fmt)
    if (identical(fmt_lower, "pdf") && isTRUE(capabilities("cairo"))) {
      ggsave(
        output,
        plot = plot,
        width = width,
        height = height,
        units = "in",
        device = grDevices::cairo_pdf,
        limitsize = FALSE
      )
    } else {
      ggsave(
        output,
        plot = plot,
        width = width,
        height = height,
        units = "in",
        dpi = 300,
        limitsize = FALSE
      )
    }
    message("Wrote ", output)
  }
}

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
      legend.title = element_blank(),
      legend.key.height = grid::unit(0.35, "lines"),
      plot.title = element_blank(),
      plot.caption = element_text(hjust = 0, size = base_size - 1, color = "#4D4D4D"),
      plot.margin = margin(6, 10, 6, 6)
    )
}

safe_numeric <- function(x) suppressWarnings(as.numeric(x))

lookup_labels <- function(x, label_map, fallback = NULL) {
  x_chr <- as.character(x)
  out <- unname(label_map[x_chr])
  if (is.null(fallback)) {
    fallback <- x_chr
  }
  fallback <- as.character(fallback)
  if (length(fallback) == 1L && length(x_chr) > 1L) {
    fallback <- rep(fallback, length(x_chr))
  }
  missing <- is.na(out) | out == ""
  out[missing] <- fallback[missing]
  str_squish(out)
}

column_or <- function(df, column, fallback) {
  if (column %in% names(df)) {
    df[[column]]
  } else {
    fallback
  }
}

label_dataset <- function(df) {
  dataset_id <- column_or(df, "dataset_id", rep("", nrow(df)))
  fallback <- column_or(df, "dataset_display_name", dataset_id)
  lookup_labels(dataset_id, DATASET_LABELS, fallback)
}

label_condition <- function(df) {
  condition_id <- column_or(df, "condition_id", rep("", nrow(df)))
  fallback <- column_or(df, "condition_display_name", condition_id)
  lookup_labels(condition_id, CONDITION_LABELS, fallback)
}

label_output_mode <- function(x) {
  lookup_labels(x, OUTPUT_MODE_LABELS, str_replace_all(as.character(x), "_", " "))
}

label_input_format <- function(x) {
  lookup_labels(x, INPUT_FORMAT_LABELS, str_to_title(as.character(x)))
}

label_tool <- function(df) {
  tool_id <- column_or(df, "tool_id", rep("", nrow(df)))
  fallback <- column_or(df, "tool", tool_id)
  lookup_labels(tool_id, TOOL_LABELS, fallback)
}

benchmark_label <- function(df) {
  paste(label_dataset(df), label_condition(df), sep = "\n")
}

rank_with_fallback <- function(values, preferred_order) {
  values <- as.character(values)
  ranks <- match(values, preferred_order)
  missing <- is.na(ranks)
  if (any(missing)) {
    ranks[missing] <- length(preferred_order) + seq_len(sum(missing))
  }
  ranks
}

benchmark_levels <- function(df) {
  labels <- benchmark_label(df)
  dataset_rank <- rank_with_fallback(
    column_or(df, "dataset_id", rep("", nrow(df))),
    DATASET_ORDER
  )
  condition_rank <- rank_with_fallback(
    column_or(df, "condition_id", rep("", nrow(df))),
    CONDITION_ORDER
  )
  order_df <- data.frame(
    label = labels,
    dataset_rank = dataset_rank,
    condition_rank = condition_rank,
    row_rank = seq_along(labels),
    stringsAsFactors = FALSE
  ) |>
    arrange(dataset_rank, condition_rank, row_rank)
  unique(order_df$label)
}

benchmark_factor <- function(df, reverse = FALSE) {
  levels <- benchmark_levels(df)
  if (isTRUE(reverse)) {
    levels <- rev(levels)
  }
  factor(benchmark_label(df), levels = levels)
}

format_seconds <- function(x) {
  case_when(
    is.na(x) ~ "",
    abs(x) >= 100 ~ number(x, accuracy = 1, big.mark = ","),
    abs(x) >= 10 ~ number(x, accuracy = 0.1, big.mark = ","),
    TRUE ~ number(x, accuracy = 0.01, big.mark = ",")
  )
}

format_rate <- function(x) {
  case_when(
    is.na(x) ~ "",
    abs(x) >= 100 ~ number(x, accuracy = 1, big.mark = ","),
    abs(x) >= 10 ~ number(x, accuracy = 0.1, big.mark = ","),
    TRUE ~ number(x, accuracy = 0.01, big.mark = ",")
  )
}

format_xfold <- function(x) {
  case_when(
    is.na(x) ~ "",
    abs(x) >= 100 ~ paste0(number(x, accuracy = 1, big.mark = ","), "x"),
    abs(x) >= 10 ~ paste0(number(x, accuracy = 0.1, big.mark = ","), "x"),
    TRUE ~ paste0(number(x, accuracy = 0.01, big.mark = ","), "x")
  )
}

require_columns <- function(df, columns, context) {
  missing <- setdiff(columns, names(df))
  if (length(missing) > 0) {
    stop(context, ": missing required columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }
  invisible(df)
}

require_pass_rows <- function(df, context) {
  if ("status" %in% names(df)) {
    bad <- df |> filter(is.na(status) | status != "PASS")
    if (nrow(bad) > 0) {
      stop(
        context,
        ": refusing to plot ", nrow(bad),
        " non-PASS row(s). Fix upstream checks or inspect the table first.",
        call. = FALSE
      )
    }
  }
  df
}

require_positive <- function(df, column, context) {
  if (any(is.na(df[[column]]) | df[[column]] <= 0)) {
    stop(context, ": column ", column, " must be positive for this plot", call. = FALSE)
  }
  df
}

plot_input_format <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  require_columns(
    df,
    c("dataset_id", "condition_id", "input_format", "median_wall_seconds", "relative_to_fastest_median"),
    "input-format figure"
  )
  df <- df |>
    require_pass_rows("input-format figure") |>
    mutate(
      median_wall_seconds = safe_numeric(median_wall_seconds),
      relative_to_fastest_median = safe_numeric(relative_to_fastest_median)
    )
  df$benchmark <- benchmark_factor(df)
  df$input_format_label <- factor(
    label_input_format(df$input_format),
    levels = c("Plain FASTA", "gzip FASTA")
  )
  df$value_label <- paste0(
    format_seconds(df$median_wall_seconds), " s\n",
    format_xfold(df$relative_to_fastest_median), " fastest"
  )

  p <- ggplot(df, aes(x = input_format_label, y = median_wall_seconds, fill = input_format_label)) +
    geom_col(width = 0.62) +
    geom_text(aes(label = value_label), vjust = -0.25, size = 2.8, lineheight = 0.9) +
    facet_wrap(vars(benchmark), nrow = 1) +
    scale_fill_manual(
      values = c("Plain FASTA" = SEABORN[["blue"]], "gzip FASTA" = SEABORN[["orange"]]),
      drop = FALSE
    ) +
    scale_y_continuous(labels = format_seconds, expand = expansion(mult = c(0, 0.22))) +
    labs(x = NULL, y = "Median wall time (s)") +
    base_theme() +
    theme(legend.position = "none")
  write_plot(p, "figure_06_input_format", width = 5.2, height = 3.4)
}

plot_screening_speed <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  require_columns(
    df,
    c("dataset_id", "condition_id", "candidate_pairs_per_second_median"),
    "screening-speed figure"
  )
  df <- df |>
    require_pass_rows("screening-speed figure") |>
    mutate(candidate_pairs_per_second_median = safe_numeric(candidate_pairs_per_second_median))
  df$benchmark <- benchmark_factor(df, reverse = TRUE)
  df$value_label <- paste0(format_rate(df$candidate_pairs_per_second_median), " pairs/s")

  p <- ggplot(df, aes(x = candidate_pairs_per_second_median, y = benchmark)) +
    geom_col(width = 0.55, fill = SEABORN[["blue"]]) +
    geom_text(aes(label = value_label), hjust = -0.12, size = 3.0) +
    scale_x_continuous(labels = format_rate, expand = expansion(mult = c(0, 0.22))) +
    coord_cartesian(clip = "off") +
    labs(x = "Median candidate pairs per second", y = NULL) +
    base_theme() +
    theme(panel.grid.major.y = element_blank())
  write_plot(p, "figure_05_screening_speed", width = 6.2, height = 2.7)
}

plot_thread_scaling <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  require_columns(
    df,
    c("dataset_id", "condition_id", "output_mode", "threads", "speedup_vs_1_thread_median"),
    "thread-scaling figure"
  )
  df <- df |>
    require_pass_rows("thread-scaling figure") |>
    mutate(
      threads = safe_numeric(threads),
      speedup_vs_1_thread_median = safe_numeric(speedup_vs_1_thread_median)
    )
  df$benchmark <- benchmark_factor(df)
  df$output_mode_label <- factor(
    label_output_mode(df$output_mode),
    levels = c("JSON summary", "Fragment TSV")
  )

  y_min <- min(0.95, min(df$speedup_vs_1_thread_median, na.rm = TRUE) * 0.98)
  y_max <- max(1.05, max(df$speedup_vs_1_thread_median, na.rm = TRUE) * 1.06)

  p <- ggplot(
    df,
    aes(
      x = threads,
      y = speedup_vs_1_thread_median,
      color = output_mode_label,
      group = output_mode_label
    )
  ) +
    geom_hline(yintercept = 1, linetype = "dashed", color = SEABORN[["gray"]], linewidth = 0.35) +
    geom_line(linewidth = 0.7) +
    geom_point(size = 2.3) +
    facet_wrap(vars(benchmark), nrow = 1) +
    scale_color_manual(
      values = c("JSON summary" = SEABORN[["blue"]], "Fragment TSV" = SEABORN[["orange"]]),
      drop = FALSE
    ) +
    scale_x_continuous(breaks = sort(unique(df$threads))) +
    scale_y_continuous(labels = label_number(accuracy = 0.01, suffix = "x")) +
    coord_cartesian(ylim = c(y_min, y_max)) +
    labs(x = "Threads", y = "Median speedup vs. 1 thread") +
    base_theme()
  write_plot(p, "figure_s02_thread_scaling", width = 7.0, height = 3.8)
}

plot_pair_screen_scaling <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  require_columns(
    df,
    c("dataset_id", "condition_id", "jobs", "speedup_vs_1_job_median"),
    "pair-screen scaling figure"
  )
  df <- df |>
    require_pass_rows("pair-screen scaling figure") |>
    mutate(
      jobs = safe_numeric(jobs),
      speedup_vs_1_job_median = safe_numeric(speedup_vs_1_job_median)
    )
  df$benchmark <- benchmark_factor(df)

  observed <- df |>
    transmute(benchmark, jobs, speedup = speedup_vs_1_job_median, series = "Observed")
  ideal <- df |>
    distinct(benchmark, jobs) |>
    transmute(benchmark, jobs, speedup = jobs, series = "Ideal linear")
  plot_df <- bind_rows(observed, ideal) |>
    mutate(series = factor(series, levels = c("Observed", "Ideal linear")))

  min_speedup <- min(plot_df$speedup, na.rm = TRUE)
  max_speedup <- max(plot_df$speedup, na.rm = TRUE)
  y_min <- min(0.95, min_speedup * 0.98)
  y_max <- if (max_speedup <= 1) 1.05 else max_speedup * 1.03

  p <- ggplot(plot_df, aes(x = jobs, y = speedup, color = series, linetype = series, group = series)) +
    geom_line(linewidth = 0.75) +
    geom_point(data = observed, aes(x = jobs, y = speedup), size = 2.4, inherit.aes = FALSE, color = SEABORN[["blue"]]) +
    facet_wrap(vars(benchmark), nrow = 1) +
    scale_color_manual(values = c("Observed" = SEABORN[["blue"]], "Ideal linear" = SEABORN[["orange"]])) +
    scale_linetype_manual(values = c("Observed" = "solid", "Ideal linear" = "dashed")) +
    scale_x_continuous(breaks = sort(unique(df$jobs))) +
    scale_y_continuous(
      breaks = sort(unique(c(1, df$jobs))),
      labels = label_number(accuracy = 1, suffix = "x"),
      limits = c(y_min, y_max),
      expand = expansion(mult = c(0.02, 0.05))
    ) +
    labs(x = "Screening jobs", y = "Median speedup vs. 1 job") +
    base_theme()
  write_plot(p, "figure_s03_pair_screen_job_scaling", width = 6.2, height = 3.8)
}

plot_large_genome <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  require_columns(
    df,
    c("dataset_id", "condition_id", "output_mode", "median_wall_seconds"),
    "large-genome figure"
  )
  df <- df |>
    require_pass_rows("large-genome figure") |>
    mutate(median_wall_seconds = safe_numeric(median_wall_seconds))
  df$benchmark <- benchmark_factor(df, reverse = TRUE)
  df$output_mode_label <- factor(
    label_output_mode(df$output_mode),
    levels = c("JSON summary", "Fragment TSV")
  )
  df$value_label <- paste0(format_seconds(df$median_wall_seconds), " s")

  p <- ggplot(df, aes(x = median_wall_seconds, y = benchmark, fill = output_mode_label)) +
    geom_col(width = 0.55) +
    geom_text(aes(label = value_label), hjust = -0.12, size = 3.0) +
    scale_fill_manual(
      values = c("JSON summary" = SEABORN[["blue"]], "Fragment TSV" = SEABORN[["orange"]]),
      drop = FALSE
    ) +
    scale_x_continuous(labels = format_seconds, expand = expansion(mult = c(0, 0.18))) +
    coord_cartesian(clip = "off") +
    labs(x = "Median wall time (s)", y = NULL) +
    base_theme() +
    theme(panel.grid.major.y = element_blank())
  if (n_distinct(df$output_mode_label) == 1) {
    p <- p + theme(legend.position = "none")
  }
  write_plot(p, "figure_s04_large_genome", width = 6.4, height = 2.8)
}

plot_matched_timing <- function(path) {
  df <- read_table(path)
  if (is.null(df) || nrow(df) == 0) return(invisible(FALSE))
  require_columns(
    df,
    c("dataset_id", "condition_id", "tool_id", "tool", "median_wall_seconds", "relative_to_radigest_median"),
    "matched-tool timing figure"
  )
  df <- df |>
    require_pass_rows("matched-tool timing figure") |>
    mutate(
      median_wall_seconds = safe_numeric(median_wall_seconds),
      relative_to_radigest_median = safe_numeric(relative_to_radigest_median),
      tool_group = factor(
        if_else(tool_id == "radigest", "radigest", "Comparator"),
        levels = c("radigest", "Comparator")
      ),
      relative_label = if_else(tool_id == "radigest", "1x", format_xfold(relative_to_radigest_median)),
      label_x = median_wall_seconds * if_else(tool_id == "radigest", 1.22, 1.18)
    ) |>
    require_positive("median_wall_seconds", "matched-tool timing figure")
  df$benchmark <- benchmark_factor(df)
  tool_levels <- df |>
    transmute(tool_label = label_tool(df), tool_rank = rank_with_fallback(tool_id, TOOL_ORDER)) |>
    distinct(tool_label, tool_rank) |>
    arrange(tool_rank) |>
    pull(tool_label)
  df$tool_label <- factor(label_tool(df), levels = rev(tool_levels))

  p <- ggplot(df, aes(x = median_wall_seconds, y = tool_label, color = tool_group)) +
    geom_point(size = 2.6) +
    geom_text(
      aes(x = label_x, label = relative_label),
      hjust = 0,
      size = 2.5,
      color = SEABORN[["dark_gray"]],
      show.legend = FALSE
    ) +
    facet_wrap(vars(benchmark), ncol = 1) +
    scale_color_manual(
      values = c("radigest" = SEABORN[["blue"]], "Comparator" = SEABORN[["gray"]]),
      breaks = c("radigest", "Comparator")
    ) +
    scale_x_log10(
      breaks = breaks_log(n = 6),
      labels = format_seconds,
      expand = expansion(mult = c(0.02, 0.30))
    ) +
    coord_cartesian(clip = "off") +
    labs(x = "Median wall time (s, log scale)", y = NULL) +
    base_theme() +
    theme(panel.grid.major.y = element_blank())
  matched_height <- max(5.2, 2.35 * n_distinct(df$benchmark) + 0.65)
  write_plot(p, "figure_04_matched_tool_timing", width = 7.2, height = matched_height)
}

plot_input_format(input_format_path)
plot_screening_speed(screening_speed_path)
plot_thread_scaling(thread_scaling_path)
plot_pair_screen_scaling(pair_screen_path)
plot_large_genome(large_genome_path)
plot_matched_timing(matched_timing_path)
