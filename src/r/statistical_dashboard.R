# Phase 557: Statistical Dashboard — 드론 비행 통계 대시보드 (R)
# Statistical analysis and outlier detection for swarm drone telemetry.

library(stats)

PHASE <- 557

# ── Data generation ────────────────────────────────────────────────

#' Generate synthetic drone telemetry data.
generate_telemetry <- function(n_drones = 10, n_steps = 100, seed = 42) {
  set.seed(seed)
  records <- vector("list", n_drones * n_steps)
  idx <- 1
  for (d in seq_len(n_drones)) {
    battery <- 100
    x <- 0; y <- 0; z <- 50
    for (t in seq_len(n_steps)) {
      battery <- battery - runif(1, 0.1, 0.3)
      x <- x + rnorm(1, 0, 1)
      y <- y + rnorm(1, 0, 1)
      z <- z + rnorm(1, 0, 0.5)
      records[[idx]] <- list(
        drone_id = d,
        step     = t,
        battery  = battery,
        x = x, y = y, z = z,
        velocity = runif(1, 2, 15)
      )
      idx <- idx + 1
    }
  }
  do.call(rbind, lapply(records, as.data.frame))
}

# ── Summary statistics ─────────────────────────────────────────────

#' Compute per-drone summary statistics.
drone_summary <- function(df) {
  tapply(df$battery, df$drone_id, function(b) {
    c(mean = mean(b), sd = sd(b), min = min(b), max = max(b))
  })
}

#' Compute fleet-wide statistics.
fleet_stats <- function(df) {
  list(
    velocity_mean   = mean(df$velocity),
    velocity_sd     = sd(df$velocity),
    battery_mean    = mean(df$battery),
    altitude_range  = range(df$z),
    n_records       = nrow(df)
  )
}

# ── Outlier detection ──────────────────────────────────────────────

#' Detect battery outliers using IQR method.
detect_outliers <- function(df, col = "battery") {
  vals <- df[[col]]
  q1   <- quantile(vals, 0.25)
  q3   <- quantile(vals, 0.75)
  iqr  <- q3 - q1
  lower <- q1 - 1.5 * iqr
  upper <- q3 + 1.5 * iqr
  outlier_rows <- df[vals < lower | vals > upper, ]
  list(
    outlier_count = nrow(outlier_rows),
    lower_fence   = lower,
    upper_fence   = upper,
    outlier_ids   = unique(outlier_rows$drone_id)
  )
}

#' Z-score based anomaly detection on velocity.
zscore_anomalies <- function(df, threshold = 3.0) {
  mu  <- mean(df$velocity)
  sig <- sd(df$velocity)
  df$z_score <- abs((df$velocity - mu) / sig)
  df[df$z_score > threshold, ]
}

# ── Trend analysis ─────────────────────────────────────────────────

#' Fit linear trend to battery drain over steps.
battery_trend <- function(df, drone_id = 1) {
  sub <- df[df$drone_id == drone_id, ]
  model <- lm(battery ~ step, data = sub)
  summary(model)
}

# ── Main execution ─────────────────────────────────────────────────

main <- function() {
  cat(sprintf("Phase %d: Statistical Dashboard — 드론 통계 대시보드\n", PHASE))
  df <- generate_telemetry(n_drones = 10, n_steps = 50)
  cat(sprintf("Generated %d records\n", nrow(df)))

  stats <- fleet_stats(df)
  cat(sprintf("Velocity: mean=%.2f sd=%.2f\n", stats$velocity_mean, stats$velocity_sd))
  cat(sprintf("Battery: mean=%.2f\n", stats$battery_mean))

  outliers <- detect_outliers(df)
  cat(sprintf("Outliers detected: %d\n", outliers$outlier_count))

  anom <- zscore_anomalies(df)
  cat(sprintf("Z-score anomalies (|z|>3): %d rows\n", nrow(anom)))

  cat(sprintf("Phase %d complete.\n", PHASE))
  invisible(list(df = df, stats = stats, outliers = outliers))
}

main()
