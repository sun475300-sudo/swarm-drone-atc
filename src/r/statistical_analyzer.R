# Statistical Analyzer — R module for Phase 617
# Comprehensive statistical analysis toolkit for drone swarm performance metrics.

# ===== Setup =====

set.seed(42)
N_DRONES <- 25
N_STEPS <- 200

# ===== Data Generation =====

#' Generate comprehensive swarm performance dataset
generate_swarm_data <- function(n_drones, n_steps) {
  drones <- paste0("D", sprintf("%03d", seq_len(n_drones)))
  n <- n_drones * n_steps
  data.frame(
    drone_id      = rep(drones, each = n_steps),
    step          = rep(seq_len(n_steps), times = n_drones),
    time_s        = rep(seq(0, by = 0.1, length.out = n_steps), times = n_drones),
    altitude      = pmax(0, rnorm(n, 75, 12)),
    battery       = pmax(0, pmin(100, 100 - runif(n, 0, 70))),
    speed         = pmax(0, rnorm(n, 9, 2.5)),
    separation    = pmax(0, rnorm(n, 25, 8)),
    rssi_dbm      = rnorm(n, -68, 7),
    cpu_temp_c    = rnorm(n, 45, 5),
    mission_score = pmax(0, pmin(1, rnorm(n, 0.78, 0.12))),
    conflict_risk = runif(n) < 0.05
  )
}

# ===== Descriptive Statistics =====

#' Compute full descriptive statistics for a numeric vector
full_stats <- function(x, name = "variable") {
  x <- x[!is.na(x)]
  list(
    name     = name,
    n        = length(x),
    mean     = mean(x),
    sd       = sd(x),
    se       = sd(x) / sqrt(length(x)),
    median   = median(x),
    iqr      = IQR(x),
    cv       = sd(x) / mean(x),  # coefficient of variation
    min      = min(x),
    max      = max(x),
    q10      = quantile(x, 0.10),
    q25      = quantile(x, 0.25),
    q75      = quantile(x, 0.75),
    q90      = quantile(x, 0.90),
    skewness = mean((x - mean(x))^3) / sd(x)^3,
    kurtosis = mean((x - mean(x))^4) / sd(x)^4 - 3
  )
}

#' Print a formatted stats summary
print_stats <- function(s) {
  cat(sprintf("\n--- %s ---\n", s$name))
  cat(sprintf("  N: %d | Mean: %.3f | SD: %.3f | CV: %.3f\n", s$n, s$mean, s$sd, s$cv))
  cat(sprintf("  Median: %.3f | IQR: %.3f\n", s$median, s$iqr))
  cat(sprintf("  Range: [%.3f, %.3f]\n", s$min, s$max))
  cat(sprintf("  Skewness: %.3f | Kurtosis: %.3f\n", s$skewness, s$kurtosis))
}

# ===== Outlier Detection =====

#' Z-score based outlier flag
flag_outliers_z <- function(x, threshold = 2.5) abs(scale(x)) > threshold

#' Modified Z-score (robust to non-normal distributions)
flag_outliers_mad <- function(x, threshold = 3.5) {
  med <- median(x, na.rm = TRUE)
  mad_val <- median(abs(x - med), na.rm = TRUE)
  if (mad_val == 0) return(rep(FALSE, length(x)))
  mz <- 0.6745 * (x - med) / mad_val
  abs(mz) > threshold
}

#' Run outlier analysis on key metrics
run_outlier_analysis <- function(df) {
  metrics <- c("altitude", "battery", "speed", "separation", "rssi_dbm")
  lapply(metrics, function(m) {
    z_flags <- flag_outliers_z(df[[m]])
    mad_flags <- flag_outliers_mad(df[[m]])
    list(
      metric       = m,
      n_z_outlier  = sum(z_flags, na.rm = TRUE),
      n_mad_outlier = sum(mad_flags, na.rm = TRUE),
      pct_outlier  = round(100 * mean(z_flags, na.rm = TRUE), 2)
    )
  })
}

# ===== Hypothesis Tests =====

#' Compare two drone groups on battery metric
compare_groups <- function(df) {
  # Split into first half and second half drones
  drone_list <- unique(df$drone_id)
  g1 <- df[df$drone_id %in% drone_list[1:(length(drone_list)/2)], "battery"]
  g2 <- df[df$drone_id %in% drone_list[(length(drone_list)/2 + 1):length(drone_list)], "battery"]

  list(
    group1_mean = mean(g1),
    group2_mean = mean(g2),
    difference  = mean(g1) - mean(g2),
    pooled_sd   = sqrt((var(g1) + var(g2)) / 2)
  )
}

# ===== Correlation Analysis =====

#' Compute correlation matrix for numeric columns
compute_correlations <- function(df) {
  num_cols <- c("altitude", "battery", "speed", "separation", "mission_score")
  cor(df[, num_cols], use = "pairwise.complete.obs")
}

# ===== Main Report =====

cat("=== Statistical Analyzer: Phase 617 ===\n")
df <- generate_swarm_data(N_DRONES, N_STEPS)
cat(sprintf("Dataset: %d drones × %d steps = %d records\n", N_DRONES, N_STEPS, nrow(df)))

# Print stats for key variables
for (col in c("altitude", "battery", "speed", "mission_score")) {
  s <- full_stats(df[[col]], col)
  print_stats(s)
}

cat("\n=== Outlier Analysis ===\n")
outliers <- run_outlier_analysis(df)
for (o in outliers) {
  cat(sprintf("  %s: %d z-outliers (%.2f%%), %d MAD-outliers\n",
              o$metric, o$n_z_outlier, o$pct_outlier, o$n_mad_outlier))
}

cat("\n=== Group Comparison ===\n")
cmp <- compare_groups(df)
cat(sprintf("  Group 1 battery: %.2f%% | Group 2: %.2f%%\n", cmp$group1_mean, cmp$group2_mean))
cat(sprintf("  Difference: %.3f | Pooled SD: %.3f\n", cmp$difference, cmp$pooled_sd))

cat("\nStatistical analysis complete.\n")
