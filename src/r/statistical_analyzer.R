# Phase 617: statistical_analyzer — R 기반 통계 분석기
# SDACS Statistical Analyzer for Swarm Performance Metrics

# 기본 통계량 계산
compute_summary_stats <- function(x) {
  x <- x[!is.na(x)]
  n <- length(x)
  if (n == 0) return(NULL)
  list(
    n      = n,
    mean   = mean(x),
    sd     = sd(x),
    median = median(x),
    q25    = quantile(x, 0.25),
    q75    = quantile(x, 0.75),
    min    = min(x),
    max    = max(x),
    iqr    = IQR(x),
    skew   = if (n >= 3) {
               m3 <- mean((x - mean(x))^3)
               m3 / (sd(x)^3 + 1e-12)
             } else NA_real_
  )
}

# 이상치(outlier) 탐지 — Z-score 방법
detect_outliers_zscore <- function(x, threshold = 3.0) {
  z <- (x - mean(x, na.rm = TRUE)) / (sd(x, na.rm = TRUE) + 1e-12)
  outlier_idx <- which(abs(z) > threshold)
  list(
    indices = outlier_idx,
    values  = x[outlier_idx],
    z_scores = z[outlier_idx],
    count   = length(outlier_idx)
  )
}

# 이상치 탐지 — IQR 방법
detect_outliers_iqr <- function(x, iqr_factor = 1.5) {
  q1  <- quantile(x, 0.25, na.rm = TRUE)
  q3  <- quantile(x, 0.75, na.rm = TRUE)
  iqr <- q3 - q1
  lower <- q1 - iqr_factor * iqr
  upper <- q3 + iqr_factor * iqr
  outlier_idx <- which(x < lower | x > upper)
  list(
    indices = outlier_idx,
    values  = x[outlier_idx],
    lower   = lower,
    upper   = upper,
    count   = length(outlier_idx)
  )
}

# 드론 메트릭 분석
analyze_drone_metrics <- function(data) {
  results <- list()
  metrics <- c("battery", "altitude", "speed", "separation")
  for (m in metrics) {
    if (m %in% colnames(data)) {
      vals <- data[[m]]
      stats   <- compute_summary_stats(vals)
      outlier <- detect_outliers_iqr(vals)
      results[[m]] <- list(stats = stats, outliers = outlier)
    }
  }
  return(results)
}

# 군집 분산 지수 계산 (Swarm Dispersion Index)
swarm_dispersion_index <- function(lats, lons, alts) {
  n <- length(lats)
  if (n < 2) return(0.0)
  centroid_lat <- mean(lats)
  centroid_lon <- mean(lons)
  centroid_alt <- mean(alts)
  dists <- sqrt(
    ((lats - centroid_lat) * 111320)^2 +
    ((lons - centroid_lon) * 111320)^2 +
    (alts - centroid_alt)^2
  )
  mean(dists)
}

# 시계열 추세 분석 (선형 회귀)
analyze_trend <- function(x, times = NULL) {
  n <- length(x)
  if (is.null(times)) times <- seq_len(n)
  fit <- lm(x ~ times)
  list(
    slope     = coef(fit)[2],
    intercept = coef(fit)[1],
    r_squared = summary(fit)$r.squared,
    trend     = if (coef(fit)[2] > 0) "increasing" else if (coef(fit)[2] < 0) "decreasing" else "stable"
  )
}

# 메인 분석 실행
main <- function() {
  cat("SDACS Statistical Analyzer — Phase 617\n\n")
  set.seed(42)
  n <- 100
  data <- data.frame(
    drone_id   = rep(0:4, each = n / 5),
    battery    = pmax(0, 100 - cumsum(runif(n, 0, 1))),
    altitude   = 50 + rnorm(n, 0, 5),
    speed      = pmax(0, rnorm(n, 5, 1)),
    separation = pmax(0, rnorm(n, 20, 5))
  )

  results <- analyze_drone_metrics(data)
  for (m in names(results)) {
    s <- results[[m]]$stats
    o <- results[[m]]$outliers
    cat(sprintf("%s: mean=%.2f sd=%.2f outliers=%d\n",
        m, s$mean, s$sd, o$count))
  }

  # 배터리 소모 추세
  bat_trend <- analyze_trend(data$battery)
  cat(sprintf("\n배터리 추세: %s (slope=%.4f, R²=%.3f)\n",
      bat_trend$trend, bat_trend$slope, bat_trend$r_squared))

  # 군집 분산 지수
  sdi <- swarm_dispersion_index(
    lats = runif(5, 37.49, 37.52),
    lons = runif(5, 126.99, 127.03),
    alts = runif(5, 45, 65)
  )
  cat(sprintf("군집 분산 지수: %.2fm\n", sdi))
}

main()
