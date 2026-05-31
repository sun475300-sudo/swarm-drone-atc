# Phase 557: Statistical Dashboard for Swarm Drone Analytics
# Real-time statistical analysis with outlier detection
# SDACS Analytics Engine

library(stats)

# ── Data structures ───────────────────────────────────────────────────────────

# Telemetry data frame structure
create_telemetry_df <- function(n = 100, seed = 42) {
  set.seed(seed)
  data.frame(
    drone_id = sample(paste0("D", 1:10), n, replace = TRUE),
    timestamp = seq(0, n - 1, by = 1),
    altitude = rnorm(n, mean = 100, sd = 10),
    battery  = pmax(0, rnorm(n, mean = 75, sd = 15)),
    velocity = pmax(0, rnorm(n, mean = 8, sd = 2)),
    conflicts = rpois(n, lambda = 0.5)
  )
}

# ── Statistical functions ──────────────────────────────────────────────────────

# Compute descriptive statistics summary
compute_summary <- function(df, col) {
  x <- df[[col]]
  list(
    mean   = mean(x, na.rm = TRUE),
    median = median(x, na.rm = TRUE),
    sd     = sd(x, na.rm = TRUE),
    min    = min(x, na.rm = TRUE),
    max    = max(x, na.rm = TRUE),
    q1     = quantile(x, 0.25, na.rm = TRUE),
    q3     = quantile(x, 0.75, na.rm = TRUE)
  )
}

# IQR-based outlier detection
detect_outliers <- function(x, method = "iqr", threshold = 1.5) {
  if (method == "iqr") {
    q1 <- quantile(x, 0.25, na.rm = TRUE)
    q3 <- quantile(x, 0.75, na.rm = TRUE)
    iqr_val <- q3 - q1
    lower <- q1 - threshold * iqr_val
    upper <- q3 + threshold * iqr_val
    outlier_idx <- which(x < lower | x > upper)
  } else if (method == "zscore") {
    z_scores <- abs(scale(x))
    outlier_idx <- which(z_scores > threshold)
  } else {
    outlier_idx <- integer(0)
  }
  list(
    indices = outlier_idx,
    count   = length(outlier_idx),
    values  = x[outlier_idx],
    method  = method
  )
}

# Time series trend analysis
analyze_trend <- function(df, col) {
  x <- df[[col]]
  t <- seq_along(x)
  model <- lm(x ~ t)
  coef_vals <- coef(model)
  list(
    intercept = as.numeric(coef_vals[1]),
    slope     = as.numeric(coef_vals[2]),
    r_squared = summary(model)$r.squared,
    trend     = ifelse(coef_vals[2] > 0, "increasing", "decreasing")
  )
}

# Compute rolling statistics
rolling_mean <- function(x, window = 5) {
  n <- length(x)
  result <- numeric(n)
  for (i in seq_along(x)) {
    start_i <- max(1, i - window + 1)
    result[i] <- mean(x[start_i:i], na.rm = TRUE)
  }
  result
}

# Drone performance scoring
score_drone <- function(df, drone_id) {
  sub_df <- df[df$drone_id == drone_id, ]
  if (nrow(sub_df) == 0) return(NULL)

  battery_mean <- mean(sub_df$battery, na.rm = TRUE)
  conflict_sum <- sum(sub_df$conflicts, na.rm = TRUE)
  alt_stability <- 1 / (1 + sd(sub_df$altitude, na.rm = TRUE))

  score <- 0.4 * battery_mean / 100 +
           0.3 * alt_stability +
           0.3 * exp(-0.1 * conflict_sum)

  list(
    drone_id        = drone_id,
    score           = score,
    battery_mean    = battery_mean,
    conflict_total  = conflict_sum,
    observations    = nrow(sub_df)
  )
}

# Fleet-wide statistical dashboard
generate_dashboard <- function(df) {
  cols <- c("altitude", "battery", "velocity")
  summaries <- lapply(cols, function(col) compute_summary(df, col))
  names(summaries) <- cols

  outlier_results <- lapply(cols, function(col) {
    detect_outliers(df[[col]], method = "iqr")
  })
  names(outlier_results) <- cols

  trend_results <- lapply(cols, function(col) analyze_trend(df, col))
  names(trend_results) <- cols

  drone_ids <- unique(df$drone_id)
  scores <- lapply(drone_ids, function(d) score_drone(df, d))

  list(
    summary   = summaries,
    outlier   = outlier_results,
    trends    = trend_results,
    scores    = scores,
    n_rows    = nrow(df),
    n_drones  = length(drone_ids)
  )
}

# ── Main ──────────────────────────────────────────────────────────────────────

telemetry <- create_telemetry_df(200)
dashboard <- generate_dashboard(telemetry)

cat("SDACS Statistical Dashboard v557\n")
cat(sprintf("Drones: %d | Records: %d\n", dashboard$n_drones, dashboard$n_rows))
cat(sprintf("Mean altitude: %.2f m\n", dashboard$summary$altitude$mean))
cat(sprintf("Battery outlier count: %d\n", dashboard$outlier$battery$count))
cat(sprintf("Velocity trend: %s\n", dashboard$trends$velocity$trend))
cat("summary and outlier analysis complete\n")
