# Statistical Analyzer — R for SDACS flight data analytics
# Phase 617

library(stats)

# ── Data Loading ─────────────────────────────────────────────────

load_telemetry <- function(filepath = NULL) {
  if (is.null(filepath)) {
    # Generate synthetic data for testing
    n <- 1000
    set.seed(42)
    data.frame(
      drone_id   = sample(paste0("D-", sprintf("%03d", 1:10)), n, replace = TRUE),
      timestamp  = seq(0, n - 1, by = 1),
      lat        = rnorm(n, 37.5665, 0.01),
      lon        = rnorm(n, 126.978, 0.01),
      alt_m      = pmax(0, rnorm(n, 100, 20)),
      batt_pct   = pmax(0, pmin(100, 85 - cumsum(rnorm(n, 0.05, 0.02)))),
      speed_mps  = pmax(0, rnorm(n, 5, 2)),
      status     = sample(c("airborne", "idle", "fault"), n, replace = TRUE,
                          prob = c(0.85, 0.12, 0.03))
    )
  } else {
    read.csv(filepath, stringsAsFactors = FALSE)
  }
}

# ── Descriptive Statistics ────────────────────────────────────────

describe_fleet <- function(df) {
  list(
    n_records   = nrow(df),
    n_drones    = length(unique(df$drone_id)),
    mean_alt    = mean(df$alt_m, na.rm = TRUE),
    sd_alt      = sd(df$alt_m, na.rm = TRUE),
    mean_batt   = mean(df$batt_pct, na.rm = TRUE),
    mean_speed  = mean(df$speed_mps, na.rm = TRUE),
    status_dist = table(df$status)
  )
}

# ── Anomaly Detection ─────────────────────────────────────────────

detect_outliers_iqr <- function(x, k = 1.5) {
  q <- quantile(x, probs = c(0.25, 0.75), na.rm = TRUE)
  iqr <- q[2] - q[1]
  lower <- q[1] - k * iqr
  upper <- q[2] + k * iqr
  list(
    outlier_indices = which(x < lower | x > upper),
    lower_bound     = lower,
    upper_bound     = upper,
    n_outliers      = sum(x < lower | x > upper, na.rm = TRUE)
  )
}

detect_speed_anomalies <- function(df, max_speed = 30.0) {
  anomalies <- df[df$speed_mps > max_speed, ]
  cat(sprintf("Speed anomalies detected: %d records (%.1f%%)\n",
              nrow(anomalies), 100 * nrow(anomalies) / nrow(df)))
  anomalies
}

detect_battery_critical <- function(df, threshold = 15.0) {
  critical <- df[df$batt_pct < threshold, ]
  cat(sprintf("Critical battery events: %d (drones: %s)\n",
              nrow(critical), paste(unique(critical$drone_id), collapse = ", ")))
  critical
}

# ── Time Series Analysis ──────────────────────────────────────────

battery_trend <- function(df, drone_id) {
  d <- df[df$drone_id == drone_id, ]
  d <- d[order(d$timestamp), ]
  if (nrow(d) < 2) return(NULL)
  lm(batt_pct ~ timestamp, data = d)
}

# ── Summary Report ────────────────────────────────────────────────

generate_report <- function(df) {
  stats <- describe_fleet(df)
  alt_outliers <- detect_outliers_iqr(df$alt_m)
  speed_outliers <- detect_outliers_iqr(df$speed_mps)

  cat("=== SDACS Statistical Analysis Report ===\n")
  cat(sprintf("Records: %d | Drones: %d\n", stats$n_records, stats$n_drones))
  cat(sprintf("Altitude   — mean=%.1fm, sd=%.1fm, outliers=%d\n",
              stats$mean_alt, stats$sd_alt, alt_outliers$n_outliers))
  cat(sprintf("Battery    — mean=%.1f%%\n", stats$mean_batt))
  cat(sprintf("Speed      — mean=%.1f m/s, outliers=%d\n",
              stats$mean_speed, speed_outliers$n_outliers))
  cat("Status distribution:\n")
  print(stats$status_dist)
  invisible(stats)
}

# ── Main ─────────────────────────────────────────────────────────

if (!interactive()) {
  df <- load_telemetry()
  generate_report(df)
}
