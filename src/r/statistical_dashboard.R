# Phase 557: statistical_dashboard — R 기반 군집 드론 통계 대시보드
# SDACS Statistical Analysis Dashboard

# 드론 텔레메트리 데이터 생성 (시뮬레이션)
generate_telemetry_data <- function(n_drones = 10, n_steps = 100) {
  set.seed(42)
  data <- data.frame(
    drone_id    = rep(0:(n_drones - 1), each = n_steps),
    step        = rep(1:n_steps, times = n_drones),
    battery     = numeric(n_drones * n_steps),
    altitude    = numeric(n_drones * n_steps),
    speed       = numeric(n_drones * n_steps),
    separation  = numeric(n_drones * n_steps),
    stringsAsFactors = FALSE
  )
  for (i in 0:(n_drones - 1)) {
    idx <- data$drone_id == i
    data$battery[idx]   <- 100 - cumsum(runif(n_steps, 0.1, 0.5))
    data$altitude[idx]  <- 50 + cumsum(rnorm(n_steps, 0, 1))
    data$speed[idx]     <- pmax(0, rnorm(n_steps, 5, 1.5))
    data$separation[idx] <- pmax(0, rnorm(n_steps, 20, 5))
  }
  return(data)
}

# 기술 통계 요약 (mean, sd, median, quantiles)
summarize_statistics <- function(df) {
  cat("=== 기술 통계 요약 ===\n")
  metrics <- c("battery", "altitude", "speed", "separation")
  result <- list()
  for (metric in metrics) {
    values <- df[[metric]]
    stats  <- c(
      mean   = mean(values, na.rm = TRUE),
      sd     = sd(values, na.rm = TRUE),
      median = median(values, na.rm = TRUE),
      q25    = quantile(values, 0.25, na.rm = TRUE),
      q75    = quantile(values, 0.75, na.rm = TRUE),
      min    = min(values, na.rm = TRUE),
      max    = max(values, na.rm = TRUE)
    )
    result[[metric]] <- stats
    cat(sprintf("%s: mean=%.2f sd=%.2f median=%.2f\n",
        metric, stats["mean"], stats["sd"], stats["median"]))
  }
  return(invisible(result))
}

# 이상치(outlier) 탐지 — IQR 방법
detect_outlier <- function(values, iqr_factor = 1.5) {
  q1  <- quantile(values, 0.25, na.rm = TRUE)
  q3  <- quantile(values, 0.75, na.rm = TRUE)
  iqr <- q3 - q1
  lower <- q1 - iqr_factor * iqr
  upper <- q3 + iqr_factor * iqr
  outlier_mask <- values < lower | values > upper
  cat(sprintf("outlier 개수: %d / %d (%.1f%%)\n",
      sum(outlier_mask, na.rm = TRUE),
      length(values),
      100 * mean(outlier_mask, na.rm = TRUE)))
  return(which(outlier_mask))
}

# 배터리 소모율 분석
analyze_battery_drain <- function(df) {
  cat("\n=== 배터리 소모율 분석 ===\n")
  drain_rates <- numeric(length(unique(df$drone_id)))
  for (i in seq_along(unique(df$drone_id))) {
    did  <- unique(df$drone_id)[i]
    vals <- df$battery[df$drone_id == did]
    drain_rates[i] <- (vals[1] - vals[length(vals)]) / length(vals)
  }
  cat(sprintf("평균 소모율: %.4f%%/step\n", mean(drain_rates)))
  cat(sprintf("최대 소모율: %.4f%%/step (드론 %d)\n",
      max(drain_rates), which.max(drain_rates) - 1))
  return(drain_rates)
}

# 충돌 위험 통계
analyze_separation_stats <- function(df, min_sep = 5.0) {
  cat("\n=== 분리 거리 통계 ===\n")
  low_sep <- df$separation[df$separation < min_sep]
  cat(sprintf("위험 근접 횟수 (<%dm): %d\n", min_sep, length(low_sep)))
  cat(sprintf("분리 거리 summary:\n"))
  print(summary(df$separation))
  outlier_idx <- detect_outlier(df$separation)
  cat(sprintf("분리 거리 outlier (IQR 기반): %d건\n", length(outlier_idx)))
  return(list(danger_count = length(low_sep), outlier_indices = outlier_idx))
}

# 시뮬레이션 실행 및 보고서 생성
main <- function() {
  cat("SDACS Statistical Dashboard — Phase 557\n\n")
  df <- generate_telemetry_data(n_drones = 5, n_steps = 50)
  cat(sprintf("데이터 형태: %d행 x %d열\n\n", nrow(df), ncol(df)))
  stats <- summarize_statistics(df)
  drain <- analyze_battery_drain(df)
  sep_stats <- analyze_separation_stats(df)
  cat(sprintf("\n총 위험 근접: %d건\n", sep_stats$danger_count))
  cat("통계 분석 완료.\n")
}

main()
