# SDACS Statistical Dashboard — R (Phase 557)
# 드론 군집 통계 대시보드: 이상치(outlier) 탐지 + 요약

library(stats)

# 드론 텔레메트리 데이터프레임 생성 (시뮬레이션)
generate_telemetry <- function(n_drones = 50, n_steps = 100, seed = 42) {
  set.seed(seed)
  data.frame(
    drone_id  = rep(paste0("D-", seq_len(n_drones)), each = n_steps),
    timestamp = rep(seq(0, n_steps - 1) * 0.1, times = n_drones),
    x         = rnorm(n_drones * n_steps, 0, 100),
    y         = rnorm(n_drones * n_steps, 0, 100),
    altitude  = pmax(0, rnorm(n_drones * n_steps, 100, 20)),
    speed     = pmax(0, rnorm(n_drones * n_steps, 10, 3)),
    battery   = pmax(0, pmin(100, rnorm(n_drones * n_steps, 80, 15)))
  )
}

# 기술 통계 요약 (mean, sd, quantiles)
fleet_summary <- function(df) {
  list(
    altitude = list(
      mean = mean(df$altitude, na.rm = TRUE),
      sd   = sd(df$altitude, na.rm = TRUE),
      summary = summary(df$altitude)
    ),
    speed = list(
      mean = mean(df$speed, na.rm = TRUE),
      sd   = sd(df$speed, na.rm = TRUE)
    ),
    battery = list(
      mean = mean(df$battery, na.rm = TRUE),
      low_count = sum(df$battery < 20, na.rm = TRUE)
    ),
    n_drones = length(unique(df$drone_id)),
    n_records = nrow(df)
  )
}

# outlier 탐지 (IQR 방법 — Phase 557)
detect_outliers <- function(x, method = "iqr", k = 1.5) {
  if (method == "iqr") {
    q <- quantile(x, probs = c(0.25, 0.75), na.rm = TRUE)
    iqr <- q[2] - q[1]
    lower <- q[1] - k * iqr
    upper <- q[2] + k * iqr
    which(x < lower | x > upper)
  } else if (method == "zscore") {
    z <- abs((x - mean(x, na.rm = TRUE)) / sd(x, na.rm = TRUE))
    which(z > 3)
  } else {
    integer(0)
  }
}

# 드론별 이상치 탐지 보고서
outlier_report <- function(df, var = "altitude") {
  results <- lapply(split(df[[var]], df$drone_id), function(vals) {
    idx <- detect_outliers(vals)
    list(outlier_count = length(idx), outlier_pct = length(idx) / length(vals) * 100)
  })
  data.frame(
    drone_id       = names(results),
    outlier_count  = sapply(results, `[[`, "outlier_count"),
    outlier_pct    = sapply(results, `[[`, "outlier_pct"),
    row.names      = NULL
  )
}

# 이동 평균 스무딩
moving_average <- function(x, window = 5) {
  n <- length(x)
  result <- numeric(n)
  for (i in seq_len(n)) {
    lo <- max(1, i - window + 1)
    result[i] <- mean(x[lo:i])
  }
  result
}

# 배터리 소모 선형 회귀
battery_regression <- function(df) {
  model <- lm(battery ~ timestamp, data = df)
  list(
    slope     = coef(model)[2],
    intercept = coef(model)[1],
    r_squared = summary(model)$r.squared
  )
}

# 메인 대시보드 출력
run_dashboard <- function(n_drones = 20, seed = 42) {
  df <- generate_telemetry(n_drones, 50, seed)
  s  <- fleet_summary(df)
  cat("=== SDACS Statistical Dashboard (Phase 557) ===\n")
  cat(sprintf("Drones: %d | Records: %d\n", s$n_drones, s$n_records))
  cat(sprintf("Altitude: mean=%.1fm  sd=%.1fm\n", s$altitude$mean, s$altitude$sd))
  cat(sprintf("Speed:    mean=%.1fm/s\n", s$speed$mean))
  cat(sprintf("Battery:  mean=%.1f%%  low_count=%d\n", s$battery$mean, s$battery$low_count))
  invisible(list(data = df, summary = s))
}
