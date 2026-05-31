# statistical_dashboard.R - Statistical dashboard for SDACS (Phase 557)
# R-based statistical analysis and anomaly detection for drone fleet

library(stats)

# Generate synthetic drone telemetry data
generate_telemetry <- function(n_drones = 20, n_timesteps = 100, seed = 42) {
  set.seed(seed)
  data <- data.frame()
  for (t in 1:n_timesteps) {
    for (i in 1:n_drones) {
      data <- rbind(data, data.frame(
        drone_id   = paste0("D-", sprintf("%03d", i)),
        timestamp  = t,
        altitude   = 50 + 10 * sin(t/10) + rnorm(1, 0, 2),
        battery    = 100 - t * 0.5 + rnorm(1, 0, 1),
        speed      = 10 + rnorm(1, 0, 1.5),
        vibration  = abs(rnorm(1, 0, 0.3))
      ))
    }
  }
  return(data)
}

# Detect outliers using Z-score method
detect_outliers <- function(values, threshold = 3.0) {
  z_scores <- abs(scale(values))
  return(which(z_scores > threshold))
}

# Summary statistics for drone fleet
fleet_summary <- function(df) {
  list(
    n_drones    = length(unique(df$drone_id)),
    n_timesteps = length(unique(df$timestamp)),
    mean_battery = mean(df$battery, na.rm = TRUE),
    sd_battery   = sd(df$battery, na.rm = TRUE),
    mean_speed   = mean(df$speed, na.rm = TRUE),
    outlier_count = length(detect_outliers(df$vibration))
  )
}

# Statistical health dashboard
build_dashboard <- function(df) {
  # Per-drone battery trend
  battery_trend <- tapply(df$battery, df$drone_id, function(v) {
    if (length(v) > 1) {
      lm_fit <- lm(v ~ seq_along(v))
      coef(lm_fit)[2]
    } else NA
  })

  # Outlier detection per metric
  altitude_outliers <- detect_outliers(df$altitude)
  vibration_outliers <- detect_outliers(df$vibration)
  battery_outliers   <- detect_outliers(df$battery)

  # Correlation analysis
  corr_matrix <- cor(df[, c("altitude", "battery", "speed", "vibration")],
                     use = "complete.obs")

  list(
    summary         = fleet_summary(df),
    battery_trend   = battery_trend,
    altitude_outliers  = length(altitude_outliers),
    vibration_outliers = length(vibration_outliers),
    battery_outliers   = length(battery_outliers),
    correlation_matrix = corr_matrix
  )
}

# Phase 557 marker
PHASE <- 557

# Run analysis
cat(sprintf("SDACS Statistical Dashboard (Phase %d)\n", PHASE))
df <- generate_telemetry(10, 50)
stats <- fleet_summary(df)
dashboard <- build_dashboard(df)

cat(sprintf("Drones: %d, Timesteps: %d\n", stats$n_drones, stats$n_timesteps))
cat(sprintf("Mean battery: %.1f%%, outliers: %d\n",
            stats$mean_battery, dashboard$battery_outliers))
