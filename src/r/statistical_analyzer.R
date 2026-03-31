# Phase 617: Statistical Analyzer — R
# MC 결과 통계 분석 + 시각화

# ── Monte Carlo Result Analyzer ──

analyze_monte_carlo <- function(results_csv) {
  data <- read.csv(results_csv)

  summary_stats <- list(
    n_runs = nrow(data),
    collision_rate = list(
      mean = mean(data$collision_rate, na.rm = TRUE),
      sd = sd(data$collision_rate, na.rm = TRUE),
      p50 = quantile(data$collision_rate, 0.50, na.rm = TRUE),
      p95 = quantile(data$collision_rate, 0.95, na.rm = TRUE),
      p99 = quantile(data$collision_rate, 0.99, na.rm = TRUE)
    ),
    resolution_rate = list(
      mean = mean(data$resolution_rate, na.rm = TRUE),
      sd = sd(data$resolution_rate, na.rm = TRUE),
      min = min(data$resolution_rate, na.rm = TRUE)
    )
  )
  return(summary_stats)
}

# ── SLA Compliance Check ──

check_sla <- function(data, thresholds) {
  violations <- list()

  if (mean(data$collision_rate) > thresholds$max_collision_rate) {
    violations <- c(violations, list(list(
      metric = "collision_rate",
      actual = mean(data$collision_rate),
      threshold = thresholds$max_collision_rate
    )))
  }

  if (mean(data$advisory_latency) > thresholds$max_latency) {
    violations <- c(violations, list(list(
      metric = "advisory_latency",
      actual = mean(data$advisory_latency),
      threshold = thresholds$max_latency
    )))
  }

  return(list(
    compliant = length(violations) == 0,
    violations = violations,
    checked_at = Sys.time()
  ))
}

# ── Confidence Interval ──

compute_ci <- function(values, confidence = 0.95) {
  n <- length(values)
  m <- mean(values, na.rm = TRUE)
  se <- sd(values, na.rm = TRUE) / sqrt(n)
  alpha <- 1 - confidence
  z <- qnorm(1 - alpha / 2)
  return(list(
    mean = m,
    lower = m - z * se,
    upper = m + z * se,
    confidence = confidence,
    n = n
  ))
}

# ── Hypothesis Test ──

compare_configurations <- function(config_a, config_b, metric) {
  test_result <- t.test(config_a[[metric]], config_b[[metric]])
  return(list(
    metric = metric,
    mean_a = mean(config_a[[metric]]),
    mean_b = mean(config_b[[metric]]),
    p_value = test_result$p.value,
    significant = test_result$p.value < 0.05,
    effect_size = (mean(config_a[[metric]]) - mean(config_b[[metric]])) /
      sqrt((var(config_a[[metric]]) + var(config_b[[metric]])) / 2)
  ))
}

# ── Sensitivity Analysis ──

sensitivity_analysis <- function(data, param_col, metric_col) {
  model <- lm(as.formula(paste(metric_col, "~", param_col)), data = data)
  return(list(
    parameter = param_col,
    metric = metric_col,
    coefficient = coef(model)[2],
    r_squared = summary(model)$r.squared,
    p_value = summary(model)$coefficients[2, 4]
  ))
}
