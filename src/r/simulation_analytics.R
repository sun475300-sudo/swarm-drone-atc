# Phase 299: R Simulation Analytics — 시뮬레이션 분석 엔진
# Bootstrap CI, Welch t-test, 추세 분석, KPI 대시보드.

library(stats)

#' Welch's t-test 수행
#' @param a 기준 그룹 데이터
#' @param b 실험 그룹 데이터
#' @return list(t_stat, p_value, significant)
welch_t_test <- function(a, b) {
  if (length(a) < 2 || length(b) < 2) {
    return(list(t_stat = 0, p_value = 1, significant = FALSE))
  }
  result <- t.test(a, b, var.equal = FALSE)
  list(
    t_stat = result$statistic,
    p_value = result$p.value,
    significant = result$p.value < 0.05
  )
}

#' Bootstrap 신뢰구간
#' @param data 데이터 벡터
#' @param n_boot 부트스트랩 반복 수
#' @param confidence 신뢰 수준
#' @return list(lower, upper, mean)
bootstrap_ci <- function(data, n_boot = 10000, confidence = 0.95) {
  n <- length(data)
  if (n < 2) return(list(lower = mean(data), upper = mean(data), mean = mean(data)))

  boot_means <- replicate(n_boot, mean(sample(data, n, replace = TRUE)))
  alpha <- 1 - confidence
  list(
    lower = quantile(boot_means, alpha / 2),
    upper = quantile(boot_means, 1 - alpha / 2),
    mean = mean(data)
  )
}

#' Cohen's d 효과 크기
#' @param a 그룹 A 데이터
#' @param b 그룹 B 데이터
#' @return Cohen's d 값
cohens_d <- function(a, b) {
  pooled_sd <- sqrt((var(a) + var(b)) / 2)
  if (pooled_sd < 1e-10) return(0)
  (mean(a) - mean(b)) / pooled_sd
}

#' 추세 분석 (선형 회귀)
#' @param values 시계열 데이터
#' @return list(trend, slope, r_squared)
trend_analysis <- function(values) {
  if (length(values) < 3) {
    return(list(trend = "insufficient_data", slope = 0, r_squared = 0))
  }
  x <- seq_along(values)
  fit <- lm(values ~ x)
  slope <- coef(fit)[2]
  r_sq <- summary(fit)$r.squared

  trend <- if (slope > 0.01) "improving"
           else if (slope < -0.01) "degrading"
           else "stable"

  list(trend = trend, slope = slope, r_squared = r_sq,
       latest = tail(values, 1), mean = mean(values), std = sd(values))
}

#' KPI 상태 평가
#' @param value 현재 값
#' @param target 목표 값
#' @param warn_threshold 경고 임계값
#' @param crit_threshold 위험 임계값
#' @return 상태 문자열
evaluate_kpi <- function(value, target = NULL, warn_threshold = NULL, crit_threshold = NULL) {
  if (!is.null(target) && abs(value - target) / max(abs(target), 1e-6) < 0.05) {
    return("on_target")
  }
  if (!is.null(crit_threshold) && value > crit_threshold) return("critical")
  if (!is.null(warn_threshold) && value > warn_threshold) return("warning")
  "ok"
}

#' ANOVA 분석 (다중 그룹 비교)
#' @param groups named list of data vectors
#' @return list(f_stat, p_value, group_means)
anova_analysis <- function(groups) {
  if (length(groups) < 2) return(list(f_stat = 0, p_value = 1))

  values <- unlist(groups)
  group_labels <- rep(names(groups), sapply(groups, length))
  df <- data.frame(value = values, group = factor(group_labels))

  fit <- aov(value ~ group, data = df)
  s <- summary(fit)

  list(
    f_stat = s[[1]]$`F value`[1],
    p_value = s[[1]]$`Pr(>F)`[1],
    group_means = sapply(groups, mean),
    group_sds = sapply(groups, sd)
  )
}

#' 시뮬레이션 분석 보고서 생성
#' @param runs_data 실행 결과 데이터프레임 (columns: run_id, metric, value)
#' @return 분석 요약 리스트
generate_report <- function(runs_data) {
  metrics <- unique(runs_data$metric)
  report <- list()

  for (m in metrics) {
    vals <- runs_data$value[runs_data$metric == m]
    ci <- bootstrap_ci(vals)
    trend <- trend_analysis(vals)

    report[[m]] <- list(
      n = length(vals),
      mean = round(mean(vals), 4),
      std = round(sd(vals), 4),
      ci_lower = round(ci$lower, 4),
      ci_upper = round(ci$upper, 4),
      trend = trend$trend,
      slope = round(trend$slope, 6)
    )
  }
  report
}

cat("SDACS Simulation Analytics Engine (R) loaded.\n")
cat("Functions: welch_t_test, bootstrap_ci, cohens_d, trend_analysis,\n")
cat("           evaluate_kpi, anova_analysis, generate_report\n")
