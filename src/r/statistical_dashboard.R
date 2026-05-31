# P557: StatisticalDashboard - R statistical analysis for drone operations
# Phase 557: Statistical analysis and outlier detection for SDACS metrics

library(stats)

# Configuration
SDACS_STATS_CONFIG <- list(
  outlier_iqr_factor = 1.5,
  confidence_level   = 0.95,
  min_samples        = 5
)

# Compute descriptive statistics for a numeric vector
compute_stats <- function(x) {
  if (length(x) < 2) {
    return(list(n = length(x), mean = NA, sd = NA, min = NA, max = NA,
                median = NA, q25 = NA, q75 = NA))
  }
  list(
    n      = length(x),
    mean   = mean(x, na.rm = TRUE),
    sd     = sd(x, na.rm = TRUE),
    min    = min(x, na.rm = TRUE),
    max    = max(x, na.rm = TRUE),
    median = median(x, na.rm = TRUE),
    q25    = quantile(x, 0.25, na.rm = TRUE),
    q75    = quantile(x, 0.75, na.rm = TRUE)
  )
}

# Detect outliers using IQR method
detect_outlier <- function(x, factor = SDACS_STATS_CONFIG$outlier_iqr_factor) {
  q25 <- quantile(x, 0.25, na.rm = TRUE)
  q75 <- quantile(x, 0.75, na.rm = TRUE)
  iqr <- q75 - q25
  lower <- q25 - factor * iqr
  upper <- q75 + factor * iqr
  list(
    is_outlier = x < lower | x > upper,
    lower_bound = lower,
    upper_bound = upper,
    outlier_count = sum(x < lower | x > upper, na.rm = TRUE)
  )
}

# Compute moving average
moving_average <- function(x, window = 5) {
  n <- length(x)
  result <- numeric(n)
  for (i in seq_len(n)) {
    start_i <- max(1, i - window + 1)
    result[i] <- mean(x[start_i:i], na.rm = TRUE)
  }
  result
}

# Analyze collision rates from simulation results
analyze_collision_rates <- function(df) {
  if (!is.data.frame(df) || !"collision_count" %in% names(df)) {
    stop("Input must be a data.frame with 'collision_count' column")
  }
  rates <- df$collision_count
  stats <- compute_stats(rates)
  outliers <- detect_outlier(rates)
  summary_text <- paste(
    sprintf("N=%d, Mean=%.3f, SD=%.3f", stats$n, stats$mean, stats$sd),
    sprintf("Outliers detected: %d", outliers$outlier_count),
    sep = "\n"
  )
  list(stats = stats, outliers = outliers, summary = summary_text)
}

# Dashboard summary function
run_dashboard_summary <- function(simulation_results) {
  cat("=== SDACS Statistical Dashboard (Phase 557) ===\n")
  metrics <- c("collision_count", "near_miss_count", "route_efficiency")
  for (m in metrics) {
    if (m %in% names(simulation_results)) {
      s <- compute_stats(simulation_results[[m]])
      cat(sprintf("[%s] mean=%.3f sd=%.3f n=%d\n", m, s$mean, s$sd, s$n))
      o <- detect_outlier(simulation_results[[m]])
      if (o$outlier_count > 0) {
        cat(sprintf("  WARNING: %d outlier(s) detected!\n", o$outlier_count))
      }
    }
  }
}
