# Phase 557: Statistical Dashboard — R
# SDACS real-time statistical analysis and anomaly detection for drone fleet

# Phase 557 marker — statistical summary, mean, outlier detection

library(stats)

# ============================================================
# Fleet telemetry data structure

create_fleet_dataset <- function(n_drones = 10, n_timesteps = 100) {
  set.seed(557)
  data.frame(
    drone_id  = rep(paste0("D", sprintf("%03d", 1:n_drones)), each = n_timesteps),
    timestep  = rep(1:n_timesteps, times = n_drones),
    battery   = pmax(0, pmin(100, c(sapply(1:n_drones, function(d) {
      start_bat <- runif(1, 70, 100)
      cumsum(c(start_bat, -abs(rnorm(n_timesteps - 1, 0.1, 0.02))))
    })))),
    altitude  = pmax(0, rnorm(n_drones * n_timesteps, 60, 8)),
    speed     = pmax(0, rnorm(n_drones * n_timesteps, 10, 2)),
    heading   = runif(n_drones * n_timesteps, 0, 360),
    wind_speed = pmax(0, rnorm(n_drones * n_timesteps, 5, 2)),
    stringsAsFactors = FALSE
  )
}

# ============================================================
# Descriptive statistics

fleet_summary <- function(df) {
  metrics <- c("battery", "altitude", "speed", "wind_speed")
  result  <- lapply(metrics, function(col) {
    x <- df[[col]]
    list(
      metric  = col,
      mean    = mean(x, na.rm = TRUE),
      median  = median(x, na.rm = TRUE),
      sd      = sd(x, na.rm = TRUE),
      min     = min(x, na.rm = TRUE),
      max     = max(x, na.rm = TRUE),
      q25     = quantile(x, 0.25, na.rm = TRUE),
      q75     = quantile(x, 0.75, na.rm = TRUE)
    )
  })
  do.call(rbind, lapply(result, as.data.frame))
}

# ============================================================
# Outlier detection using IQR method

detect_outliers <- function(df, column, k = 1.5) {
  x   <- df[[column]]
  q1  <- quantile(x, 0.25, na.rm = TRUE)
  q3  <- quantile(x, 0.75, na.rm = TRUE)
  iqr <- q3 - q1
  lower <- q1 - k * iqr
  upper <- q3 + k * iqr

  outlier_mask <- x < lower | x > upper
  list(
    n_outliers  = sum(outlier_mask, na.rm = TRUE),
    lower_bound = lower,
    upper_bound = upper,
    outlier_idx = which(outlier_mask),
    outlier_vals = x[outlier_mask]
  )
}

# Z-score based outlier detection
zscore_outliers <- function(df, column, threshold = 3.0) {
  x <- df[[column]]
  z <- (x - mean(x, na.rm = TRUE)) / sd(x, na.rm = TRUE)
  outlier_mask <- abs(z) > threshold
  list(
    n_outliers   = sum(outlier_mask, na.rm = TRUE),
    threshold    = threshold,
    outlier_idx  = which(outlier_mask),
    max_z        = max(abs(z), na.rm = TRUE)
  )
}

# ============================================================
# Battery drain rate analysis

battery_drain_analysis <- function(df) {
  by_drone <- split(df, df$drone_id)
  results <- lapply(names(by_drone), function(did) {
    d <- by_drone[[did]]
    d <- d[order(d$timestep), ]
    lm_fit <- lm(battery ~ timestep, data = d)
    list(
      drone_id    = did,
      drain_rate  = coef(lm_fit)[["timestep"]],
      r_squared   = summary(lm_fit)$r.squared,
      estimated_rtl_step = if (coef(lm_fit)[["timestep"]] < 0) {
        (20 - coef(lm_fit)[["(Intercept)"]]) / coef(lm_fit)[["timestep"]]
      } else NA
    )
  })
  do.call(rbind, lapply(results, as.data.frame))
}

# ============================================================
# Conflict risk heatmap data

conflict_risk_grid <- function(df, grid_size = 10) {
  alt_bins   <- cut(df$altitude, breaks = grid_size, labels = FALSE)
  speed_bins <- cut(df$speed,    breaks = grid_size, labels = FALSE)
  table(alt_bins, speed_bins)
}

# ============================================================
# Time-series anomaly detection (simple moving average deviation)

timeseries_anomalies <- function(df, column, window = 10, sigma = 2.0) {
  df_sorted <- df[order(df$drone_id, df$timestep), ]
  by_drone  <- split(df_sorted, df_sorted$drone_id)

  anomalies <- lapply(names(by_drone), function(did) {
    d <- by_drone[[did]]
    x <- d[[column]]
    n <- length(x)
    if (n < window) return(NULL)

    # Rolling mean and sd
    roll_mean <- filter(x, rep(1/window, window), sides = 1)
    roll_mean[1:(window-1)] <- NA
    deviation <- abs(x - roll_mean)
    threshold <- sigma * sd(x, na.rm = TRUE)
    anom_mask <- !is.na(deviation) & deviation > threshold

    if (!any(anom_mask)) return(NULL)
    data.frame(
      drone_id  = did,
      timestep  = d$timestep[anom_mask],
      value     = x[anom_mask],
      deviation = deviation[anom_mask]
    )
  })
  do.call(rbind, Filter(Negate(is.null), anomalies))
}

# ============================================================
# Fleet health report

fleet_health_report <- function(df) {
  summ <- fleet_summary(df)
  bat_outliers <- detect_outliers(df, "battery")
  speed_outliers <- zscore_outliers(df, "speed")
  drain <- battery_drain_analysis(df)
  anomalies <- timeseries_anomalies(df, "battery")

  cat("=== SDACS Fleet Health Report ===\n")
  cat(sprintf("Drones monitored: %d\n", length(unique(df$drone_id))))
  cat(sprintf("Mean battery: %.1f%%\n", mean(df$battery)))
  cat(sprintf("Battery outliers (IQR): %d\n", bat_outliers$n_outliers))
  cat(sprintf("Speed anomalies (z-score): %d\n", speed_outliers$n_outliers))
  cat(sprintf("Battery anomalies (rolling): %d\n",
              if (is.null(anomalies)) 0 else nrow(anomalies)))
  cat(sprintf("Summary:\n"))
  print(summ)
  invisible(list(summary = summ, drain = drain, anomalies = anomalies))
}

# Run demo
fleet_data <- create_fleet_dataset(10, 100)
report <- fleet_health_report(fleet_data)
