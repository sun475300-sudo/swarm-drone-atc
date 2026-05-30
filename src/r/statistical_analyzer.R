# SDACS Statistical Analyzer — R (Phase 617)
# 드론 군집 통계 분석 엔진

library(stats)

# 텔레메트리 데이터 생성 (Phase 617)
simulate_fleet_data <- function(n_drones = 30, n_steps = 100, seed = 42) {
  set.seed(seed)
  data.frame(
    drone_id  = rep(paste0("D-", seq_len(n_drones)), each = n_steps),
    t         = rep(seq(0, n_steps - 1) * 0.1, times = n_drones),
    x         = rnorm(n_drones * n_steps, 0, 200),
    y         = rnorm(n_drones * n_steps, 0, 200),
    altitude  = pmax(0, rnorm(n_drones * n_steps, 100, 25)),
    speed     = pmax(0, rnorm(n_drones * n_steps, 10, 3)),
    battery   = pmax(0, pmin(100, rnorm(n_drones * n_steps, 85, 12)))
  )
}

# 기술 통계
descriptive_stats <- function(x) {
  list(
    n      = length(x),
    mean   = mean(x, na.rm = TRUE),
    median = median(x, na.rm = TRUE),
    sd     = sd(x, na.rm = TRUE),
    min    = min(x, na.rm = TRUE),
    max    = max(x, na.rm = TRUE),
    q25    = quantile(x, 0.25, na.rm = TRUE),
    q75    = quantile(x, 0.75, na.rm = TRUE)
  )
}

# 이상치 탐지
detect_outliers_zscore <- function(x, threshold = 2.5) {
  z <- (x - mean(x, na.rm = TRUE)) / sd(x, na.rm = TRUE)
  which(abs(z) > threshold)
}

detect_outliers_iqr <- function(x, k = 1.5) {
  q <- quantile(x, probs = c(0.25, 0.75), na.rm = TRUE)
  fence_lo <- q[1] - k * (q[2] - q[1])
  fence_hi <- q[2] + k * (q[2] - q[1])
  which(x < fence_lo | x > fence_hi)
}

# 배터리 소모 트렌드 (선형 회귀)
analyze_battery_trend <- function(df) {
  model <- lm(battery ~ t, data = df)
  list(
    slope     = coef(model)["t"],
    intercept = coef(model)["(Intercept)"],
    r2        = summary(model)$r.squared,
    eta_empty = if (coef(model)["t"] < 0)
      -coef(model)["(Intercept)"] / coef(model)["t"] else Inf
  )
}

# 함대 건강도 지표
fleet_health_index <- function(df) {
  avg_bat  <- mean(df$battery, na.rm = TRUE)
  low_pct  <- mean(df$battery < 20, na.rm = TRUE) * 100
  alt_ok   <- mean(df$altitude > 0 & df$altitude < 400, na.rm = TRUE) * 100
  spd_ok   <- mean(df$speed < 20, na.rm = TRUE) * 100
  
  # 종합 건강도 (0-100)
  index <- (avg_bat / 100 * 40 + alt_ok / 100 * 30 + spd_ok / 100 * 30)
  list(
    index         = round(index, 2),
    avg_battery   = round(avg_bat, 2),
    low_bat_pct   = round(low_pct, 2),
    altitude_ok   = round(alt_ok, 2),
    speed_nominal = round(spd_ok, 2)
  )
}

# 분산분석 (드론 간 고도 차이 ANOVA)
altitude_anova <- function(df) {
  tryCatch({
    model <- aov(altitude ~ drone_id, data = df)
    sm <- summary(model)[[1]]
    list(
      f_stat  = sm[["F value"]][1],
      p_value = sm[["Pr(>F)"]][1],
      significant = sm[["Pr(>F)"]][1] < 0.05
    )
  }, error = function(e) {
    list(f_stat = NA, p_value = NA, significant = FALSE)
  })
}

# 메인 분석 실행
run_analysis <- function(n_drones = 20, seed = 42) {
  df <- simulate_fleet_data(n_drones, 60, seed)
  
  cat("=== SDACS Statistical Analyzer (Phase 617) ===\n")
  alt_stats <- descriptive_stats(df$altitude)
  cat(sprintf("Altitude: mean=%.1f  sd=%.1f  [%.1f, %.1f]\n",
    alt_stats$mean, alt_stats$sd, alt_stats$min, alt_stats$max))
  
  health <- fleet_health_index(df)
  cat(sprintf("Fleet Health Index: %.1f/100\n", health$index))
  
  outliers <- detect_outliers_zscore(df$altitude)
  cat(sprintf("Altitude outliers: %d (%.1f%%)\n",
    length(outliers), length(outliers)/nrow(df)*100))
  
  invisible(list(data = df, health = health))
}
