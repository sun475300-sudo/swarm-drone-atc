# statistical_dashboard.R
# Phase 557 — R Statistical Dashboard for swarm performance analysis.
# Computes mean/summary statistics and performs outlier detection on
# simulation telemetry and Monte Carlo sweep results.

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
required_pkgs <- c("dplyr", "ggplot2", "jsonlite", "tidyr")
missing_pkgs  <- required_pkgs[!required_pkgs %in% installed.packages()[, "Package"]]
if (length(missing_pkgs) > 0) {
  message("[557] Installing packages: ", paste(missing_pkgs, collapse = ", "))
  install.packages(missing_pkgs, repos = "https://cloud.r-project.org")
}
suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(jsonlite)
  library(tidyr)
})

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

#' Load Monte Carlo results from JSON file.
#' Returns a data.frame or NULL if the file is missing.
load_mc_results <- function(path = "results/monte_carlo_results.json") {
  if (!file.exists(path)) {
    warning("[557] Results file not found: ", path)
    return(NULL)
  }
  jsonlite::fromJSON(path, flatten = TRUE)
}

#' Generate synthetic swarm telemetry for dashboard demo.
make_demo_data <- function(n_runs = 100, seed = 557) {
  set.seed(seed)
  data.frame(
    run_id          = seq_len(n_runs),
    n_drones        = sample(5:20, n_runs, replace = TRUE),
    conflicts       = rpois(n_runs, lambda = 8),
    collisions      = rpois(n_runs, lambda = 0.5),
    resolution_rate = rbeta(n_runs, shape1 = 9, shape2 = 1),
    mean_speed      = rnorm(n_runs, mean = 5.0, sd = 1.2),
    sim_duration_s  = runif(n_runs, min = 55, max = 65)
  )
}

# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

#' Phase 557: Compute mean, sd, min, max, and quantile summary for key metrics.
compute_summary <- function(df) {
  if (is.null(df)) return(NULL)
  df %>%
    summarise(
      n_runs              = n(),
      mean_conflicts      = mean(conflicts,       na.rm = TRUE),
      sd_conflicts        = sd(conflicts,         na.rm = TRUE),
      mean_resolution     = mean(resolution_rate, na.rm = TRUE),
      mean_speed_ms       = mean(mean_speed,      na.rm = TRUE),
      p50_conflicts       = quantile(conflicts, 0.50, na.rm = TRUE),
      p95_conflicts       = quantile(conflicts, 0.95, na.rm = TRUE),
      collision_rate      = mean(collisions > 0,  na.rm = TRUE)
    )
}

#' Drone-count stratified summary using dplyr::group_by + summarise.
stratified_summary <- function(df) {
  if (is.null(df)) return(NULL)
  df %>%
    mutate(drone_tier = cut(n_drones,
                            breaks = c(0, 8, 14, Inf),
                            labels = c("small", "medium", "large"))) %>%
    group_by(drone_tier) %>%
    summarise(
      count           = n(),
      mean_conflicts  = mean(conflicts,       na.rm = TRUE),
      mean_resolution = mean(resolution_rate, na.rm = TRUE),
      .groups         = "drop"
    )
}

# ---------------------------------------------------------------------------
# Outlier detection (IQR method)
# ---------------------------------------------------------------------------

#' Detect outlier rows in `df` for column `col` using the IQR fence method.
#' An outlier value falls below Q1 - k*IQR or above Q3 + k*IQR (default k=1.5).
#'
#' Returns a list with:
#'   $outlier_rows : filtered data.frame of outlier records
#'   $lower_fence  : numeric lower fence
#'   $upper_fence  : numeric upper fence
detect_outliers <- function(df, col = "conflicts", k = 1.5) {
  if (is.null(df)) return(NULL)
  vals  <- df[[col]]
  q1    <- quantile(vals, 0.25, na.rm = TRUE)
  q3    <- quantile(vals, 0.75, na.rm = TRUE)
  iqr   <- q3 - q1
  lower <- q1 - k * iqr
  upper <- q3 + k * iqr

  outlier_rows <- df[!is.na(vals) & (vals < lower | vals > upper), ]

  list(
    outlier_rows = outlier_rows,
    lower_fence  = lower,
    upper_fence  = upper,
    n_outliers   = nrow(outlier_rows)
  )
}

# ---------------------------------------------------------------------------
# Visualisation helpers
# ---------------------------------------------------------------------------

#' Histogram of conflict counts with IQR outlier fence annotations.
plot_conflict_histogram <- function(df, out_path = NULL) {
  if (is.null(df)) return(invisible(NULL))
  oi  <- detect_outliers(df, "conflicts")
  p   <- ggplot(df, aes(x = conflicts)) +
    geom_histogram(binwidth = 1, fill = "steelblue", colour = "white", alpha = 0.8) +
    geom_vline(xintercept = oi$lower_fence, colour = "orange", linetype = "dashed") +
    geom_vline(xintercept = oi$upper_fence, colour = "red",    linetype = "dashed") +
    labs(
      title    = "[557] Conflict Count Distribution (Monte Carlo)",
      subtitle = paste0("outlier fences: [", round(oi$lower_fence, 1),
                        ", ", round(oi$upper_fence, 1), "]"),
      x        = "Conflicts per run",
      y        = "Frequency"
    ) +
    theme_minimal()
  if (!is.null(out_path)) {
    ggsave(out_path, p, width = 8, height = 5)
    message("[557] Saved histogram: ", out_path)
  }
  p
}

#' Scatter: n_drones vs resolution_rate with outlier highlights.
plot_resolution_scatter <- function(df, out_path = NULL) {
  if (is.null(df)) return(invisible(NULL))
  oi  <- detect_outliers(df, "resolution_rate", k = 2.0)
  df2 <- df %>%
    mutate(is_outlier = resolution_rate %in% oi$outlier_rows$resolution_rate)

  p <- ggplot(df2, aes(x = n_drones, y = resolution_rate, colour = is_outlier)) +
    geom_jitter(width = 0.2, alpha = 0.7) +
    scale_colour_manual(values = c("FALSE" = "steelblue", "TRUE" = "red"),
                        labels = c("normal", "outlier")) +
    labs(
      title  = "[557] Resolution Rate vs Drone Count",
      x      = "Drone count",
      y      = "Resolution rate",
      colour = NULL
    ) +
    theme_minimal()
  if (!is.null(out_path)) {
    ggsave(out_path, p, width = 8, height = 5)
    message("[557] Saved scatter: ", out_path)
  }
  p
}

# ---------------------------------------------------------------------------
# Main dashboard entry point
# ---------------------------------------------------------------------------

main <- function() {
  message("[557] Statistical Dashboard — Phase 557")

  # Try to load real results; fall back to synthetic demo data
  df <- load_mc_results()
  if (is.null(df)) {
    message("[557] No results file found — using synthetic demo data")
    df <- make_demo_data(n_runs = 120)
  }

  message("[557] ── Summary statistics ──────────────────")
  smry <- compute_summary(df)
  if (!is.null(smry)) print(smry)

  message("[557] ── Stratified summary ──────────────────")
  strat <- stratified_summary(df)
  if (!is.null(strat)) print(strat)

  message("[557] ── Outlier detection (conflicts) ───────")
  oi <- detect_outliers(df, "conflicts")
  if (!is.null(oi)) {
    cat(sprintf("  Lower fence : %.2f\n", oi$lower_fence))
    cat(sprintf("  Upper fence : %.2f\n", oi$upper_fence))
    cat(sprintf("  Outliers    : %d / %d runs\n", oi$n_outliers, nrow(df)))
  }

  # Plots (written only when not in interactive mode to avoid file side-effects)
  if (!interactive()) {
    dir.create("results", showWarnings = FALSE, recursive = TRUE)
    plot_conflict_histogram(df, out_path = "results/557_conflict_histogram.png")
    plot_resolution_scatter(df, out_path = "results/557_resolution_scatter.png")
  }

  message("[557] Dashboard complete.")
}

if (!interactive()) main()
