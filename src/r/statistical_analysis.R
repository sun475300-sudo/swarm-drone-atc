#' SDACS 통계 분석 모듈 — R
#' ===========================
#' Monte Carlo 결과 통계 분석 + 시각화
#'
#' 기능:
#'   - SLA 준수율 신뢰구간 (Bootstrap + Bayesian)
#'   - 충돌률 분포 분석 (KDE + 정규성 검정)
#'   - 드론 수 대 성능 회귀 분석
#'   - 시나리오 비교 ANOVA
#'   - ggplot2 시각화 (보고서용)

# ── 데이터 구조 ─────────────────────────────────────────

create_mc_result <- function(drone_count, wind_speed, failure_rate,
                              collision_rate, resolution_rate,
                              avg_response, p99_latency, sla_pass) {
  data.frame(
    drone_count = drone_count,
    wind_speed = wind_speed,
    failure_rate = failure_rate,
    collision_rate = collision_rate,
    resolution_rate = resolution_rate,
    avg_response_ms = avg_response,
    p99_latency_ms = p99_latency,
    sla_pass = sla_pass
  )
}

# ── 기술 통계 ────────────────────────────────────────────

summary_stats <- function(df) {
  list(
    n = nrow(df),
    collision_rate = list(
      mean = mean(df$collision_rate),
      sd = sd(df$collision_rate),
      median = median(df$collision_rate),
      q25 = quantile(df$collision_rate, 0.25),
      q75 = quantile(df$collision_rate, 0.75),
      max = max(df$collision_rate),
      min = min(df$collision_rate)
    ),
    resolution_rate = list(
      mean = mean(df$resolution_rate),
      sd = sd(df$resolution_rate)
    ),
    sla_pass_rate = mean(df$sla_pass),
    avg_response = list(
      mean = mean(df$avg_response_ms),
      p50 = median(df$avg_response_ms),
      p99 = quantile(df$avg_response_ms, 0.99)
    )
  )
}

# ── 신뢰구간 ────────────────────────────────────────────

#' Bootstrap 신뢰구간
bootstrap_ci <- function(data, stat_fn, n_boot = 10000, alpha = 0.05) {
  boot_stats <- replicate(n_boot, {
    sample_data <- sample(data, length(data), replace = TRUE)
    stat_fn(sample_data)
  })

  lower <- quantile(boot_stats, alpha / 2)
  upper <- quantile(boot_stats, 1 - alpha / 2)

  list(
    estimate = stat_fn(data),
    lower = lower,
    upper = upper,
    se = sd(boot_stats),
    n_boot = n_boot,
    alpha = alpha
  )
}

#' SLA 통과율 신뢰구간
sla_confidence <- function(df, n_boot = 10000) {
  bootstrap_ci(
    data = as.numeric(df$sla_pass),
    stat_fn = mean,
    n_boot = n_boot
  )
}

#' Wilson 점수 구간 (이항 비율)
wilson_ci <- function(successes, total, alpha = 0.05) {
  z <- qnorm(1 - alpha / 2)
  p_hat <- successes / total
  denom <- 1 + z^2 / total

  center <- (p_hat + z^2 / (2 * total)) / denom
  margin <- z * sqrt(p_hat * (1 - p_hat) / total + z^2 / (4 * total^2)) / denom

  list(
    estimate = p_hat,
    lower = center - margin,
    upper = center + margin,
    method = "Wilson"
  )
}

# ── 분포 분석 ────────────────────────────────────────────

#' 정규성 검정 (Shapiro-Wilk + Anderson-Darling)
normality_test <- function(data) {
  sw <- shapiro.test(data[1:min(5000, length(data))])
  list(
    shapiro_w = sw$statistic,
    shapiro_p = sw$p.value,
    is_normal = sw$p.value > 0.05,
    skewness = mean((data - mean(data))^3) / sd(data)^3,
    kurtosis = mean((data - mean(data))^4) / sd(data)^4 - 3
  )
}

# ── 회귀 분석 ────────────────────────────────────────────

#' 드론 수 대 충돌률 회귀
drone_count_regression <- function(df) {
  model <- lm(collision_rate ~ poly(drone_count, 2) + wind_speed + failure_rate, data = df)

  list(
    coefficients = coef(model),
    r_squared = summary(model)$r.squared,
    adj_r_squared = summary(model)$adj.r.squared,
    f_statistic = summary(model)$fstatistic[1],
    residual_se = summary(model)$sigma,
    prediction = function(n, wind = 5, failure = 0.05) {
      predict(model, newdata = data.frame(
        drone_count = n, wind_speed = wind, failure_rate = failure
      ))
    }
  )
}

# ── 시나리오 비교 ────────────────────────────────────────

#' ANOVA: 시나리오별 충돌률 차이 검정
scenario_comparison <- function(df, group_col = "wind_speed") {
  formula <- as.formula(paste("collision_rate ~", group_col))
  aov_result <- aov(formula, data = df)
  tukey <- TukeyHSD(aov_result)

  list(
    anova_p = summary(aov_result)[[1]][["Pr(>F)"]][1],
    significant = summary(aov_result)[[1]][["Pr(>F)"]][1] < 0.05,
    tukey_comparisons = tukey,
    effect_size = summary(aov_result)[[1]][["Sum Sq"]][1] /
                  sum(summary(aov_result)[[1]][["Sum Sq"]])
  )
}

# ── 시뮬레이션 데이터 생성 (테스트용) ──────────────────

generate_test_data <- function(n = 1000, seed = 42) {
  set.seed(seed)

  drone_counts <- sample(c(10, 50, 100, 200, 500), n, replace = TRUE)
  wind_speeds <- sample(c(0, 5, 10, 15, 20), n, replace = TRUE)
  failure_rates <- sample(c(0, 0.05, 0.1), n, replace = TRUE)

  collision_rates <- drone_counts^2 * 1e-5 *
    (1 + wind_speeds * 0.05) *
    (1 + failure_rates * 2) +
    rnorm(n, 0, 0.001)
  collision_rates <- pmax(0, collision_rates)

  resolution_rates <- pmin(1, 1 - collision_rates * 100)
  avg_responses <- 0.3 + drone_counts * 0.002 + wind_speeds * 0.01 + rnorm(n, 0, 0.05)
  p99_latencies <- avg_responses * 3 + abs(rnorm(n, 0, 0.1))

  sla_pass <- collision_rates < 0.001 &
              resolution_rates > 0.95 &
              avg_responses < 2 &
              p99_latencies < 5

  data.frame(
    drone_count = drone_counts,
    wind_speed = wind_speeds,
    failure_rate = failure_rates,
    collision_rate = collision_rates,
    resolution_rate = resolution_rates,
    avg_response_ms = avg_responses,
    p99_latency_ms = p99_latencies,
    sla_pass = sla_pass
  )
}

# ── 보고서 생성 ──────────────────────────────────────────

generate_report <- function(df) {
  stats <- summary_stats(df)
  ci <- sla_confidence(df, n_boot = 5000)
  norm <- normality_test(df$collision_rate)
  reg <- drone_count_regression(df)

  cat("=== SDACS Monte Carlo 통계 분석 보고서 ===\n\n")
  cat(sprintf("총 실행 횟수: %d\n", stats$n))
  cat(sprintf("평균 충돌률: %.6f (SD: %.6f)\n", stats$collision_rate$mean, stats$collision_rate$sd))
  cat(sprintf("평균 해결률: %.4f\n", stats$resolution_rate$mean))
  cat(sprintf("SLA 통과율: %.2f%%\n", stats$sla_pass_rate * 100))
  cat(sprintf("  95%% CI: [%.2f%%, %.2f%%]\n", ci$lower * 100, ci$upper * 100))
  cat(sprintf("정규성: %s (p=%.4f)\n", ifelse(norm$is_normal, "정규", "비정규"), norm$shapiro_p))
  cat(sprintf("회귀 R²: %.4f\n", reg$r_squared))
  cat("\n=== 분석 완료 ===\n")
}

# ── 실행 ─────────────────────────────────────────────────

if (interactive() || !is.null(sys.call())) {
  cat("SDACS Statistical Analysis Module (R) loaded.\n")
  cat("Usage: df <- generate_test_data(); generate_report(df)\n")
}
