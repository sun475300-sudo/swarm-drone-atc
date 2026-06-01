# Phase 557 — Statistical Dashboard for Swarm Drone Telemetry
# R module implementing statistical analysis, mean/summary statistics, and outlier detection.

# ===== Configuration =====

DRONE_COUNT <- 20
SIM_STEPS <- 100
OUTLIER_THRESHOLD <- 2.5   # standard deviations for outlier detection
SEED <- 42

set.seed(SEED)

# ===== Data Generation =====

#' Generate simulated telemetry data for a drone swarm
#' @param n_drones Number of drones
#' @param n_steps Number of simulation steps
#' @return Data frame with telemetry records
generate_telemetry <- function(n_drones, n_steps) {
  drones <- paste0("D", sprintf("%03d", 1:n_drones))
  data.frame(
    drone_id    = rep(drones, each = n_steps),
    step        = rep(1:n_steps, times = n_drones),
    x           = rnorm(n_drones * n_steps, mean = 50, sd = 20),
    y           = rnorm(n_drones * n_steps, mean = 50, sd = 20),
    altitude    = rnorm(n_drones * n_steps, mean = 80, sd = 15),
    battery     = pmax(0, 100 - runif(n_drones * n_steps, 0, 60)),
    speed       = pmax(0, rnorm(n_drones * n_steps, mean = 8, sd = 3)),
    signal_rssi = rnorm(n_drones * n_steps, mean = -70, sd = 8)
  )
}

# ===== Statistical Summary Functions =====

#' Compute basic statistics for a numeric vector
#' Wraps R's built-in mean() and summary() with additional metrics.
#' @param x Numeric vector
#' @return Named list with statistics
compute_stats <- function(x) {
  list(
    n        = length(x),
    mean     = mean(x, na.rm = TRUE),
    median   = median(x, na.rm = TRUE),
    sd       = sd(x, na.rm = TRUE),
    min      = min(x, na.rm = TRUE),
    max      = max(x, na.rm = TRUE),
    q25      = quantile(x, 0.25, na.rm = TRUE),
    q75      = quantile(x, 0.75, na.rm = TRUE),
    skewness = mean((x - mean(x))^3, na.rm = TRUE) / sd(x, na.rm = TRUE)^3
  )
}

#' Print a formatted summary of a telemetry variable
#' Uses R's summary() function for the core statistics.
#' @param df Data frame
#' @param var_name Column name to summarize
print_variable_summary <- function(df, var_name) {
  cat(sprintf("\n=== Summary: %s ===\n", var_name))
  print(summary(df[[var_name]]))
  s <- compute_stats(df[[var_name]])
  cat(sprintf("  Mean: %.2f | SD: %.2f | Skew: %.3f\n", s$mean, s$sd, s$skewness))
}

# ===== Outlier Detection =====

#' Detect outliers using Z-score method
#' @param x Numeric vector
#' @param threshold Z-score threshold (default 2.5)
#' @return Logical vector: TRUE where value is an outlier
detect_outliers_zscore <- function(x, threshold = OUTLIER_THRESHOLD) {
  z_scores <- abs((x - mean(x, na.rm = TRUE)) / sd(x, na.rm = TRUE))
  z_scores > threshold
}

#' Detect outliers using IQR method (Tukey fences)
#' @param x Numeric vector
#' @param k IQR multiplier (default 1.5)
#' @return Logical vector: TRUE where value is an outlier
detect_outliers_iqr <- function(x, k = 1.5) {
  q1 <- quantile(x, 0.25, na.rm = TRUE)
  q3 <- quantile(x, 0.75, na.rm = TRUE)
  iqr <- q3 - q1
  x < (q1 - k * iqr) | x > (q3 + k * iqr)
}

#' Run outlier analysis on all key telemetry variables
#' @param df Telemetry data frame
#' @return Data frame with outlier flags and counts
outlier_analysis <- function(df) {
  vars <- c("altitude", "battery", "speed", "signal_rssi")
  results <- lapply(vars, function(v) {
    z_outlier <- detect_outliers_zscore(df[[v]])
    iqr_outlier <- detect_outliers_iqr(df[[v]])
    data.frame(
      variable    = v,
      n_total     = nrow(df),
      n_z_outlier = sum(z_outlier, na.rm = TRUE),
      n_iqr_outlier = sum(iqr_outlier, na.rm = TRUE),
      pct_outlier = round(100 * mean(z_outlier, na.rm = TRUE), 2)
    )
  })
  do.call(rbind, results)
}

# ===== Fleet-level Dashboard =====

#' Compute per-drone aggregated statistics
#' @param df Telemetry data frame
#' @return Per-drone summary
drone_dashboard <- function(df) {
  drone_ids <- unique(df$drone_id)
  do.call(rbind, lapply(drone_ids, function(did) {
    sub <- df[df$drone_id == did, ]
    data.frame(
      drone_id        = did,
      mean_altitude   = mean(sub$altitude),
      mean_battery    = mean(sub$battery),
      mean_speed      = mean(sub$speed),
      min_battery     = min(sub$battery),
      battery_outlier = sum(detect_outliers_zscore(sub$battery))
    )
  }))
}

#' Generate full dashboard report
#' @param n_drones Number of drones
#' @param n_steps Number of steps
#' @return List with all analysis results
generate_report <- function(n_drones = DRONE_COUNT, n_steps = SIM_STEPS) {
  df <- generate_telemetry(n_drones, n_steps)

  cat(sprintf("\n=== Phase 557: Statistical Dashboard ===\n"))
  cat(sprintf("Drones: %d | Steps: %d | Records: %d\n", n_drones, n_steps, nrow(df)))

  print_variable_summary(df, "altitude")
  print_variable_summary(df, "battery")
  print_variable_summary(df, "speed")

  cat("\n=== Outlier Analysis ===\n")
  outlier_table <- outlier_analysis(df)
  print(outlier_table)

  cat("\n=== Fleet Dashboard (first 5 drones) ===\n")
  dash <- drone_dashboard(df)
  print(head(dash, 5))

  list(
    data       = df,
    outliers   = outlier_table,
    dashboard  = dash,
    n_outliers = sum(outlier_table$n_z_outlier)
  )
}

# ===== Execution =====
report <- generate_report()
cat(sprintf("\nTotal outlier detections: %d\n", report$n_outliers))
cat("Dashboard generation complete.\n")
