# Phase 617 — R Statistical Analyzer for SDACS Monte Carlo Results
# Statistical analysis and visualization of simulation data

library(stats)

#' Compute summary statistics for a numeric vector.
#' @param x numeric vector
#' @return named list with mean, sd, median, q25, q75
compute_stats <- function(x) {
  list(
    mean   = mean(x, na.rm = TRUE),
    sd     = sd(x, na.rm = TRUE),
    median = median(x, na.rm = TRUE),
    q25    = quantile(x, 0.25, na.rm = TRUE),
    q75    = quantile(x, 0.75, na.rm = TRUE),
    n      = sum(!is.na(x))
  )
}

#' Detect outliers using IQR method.
#' @param x numeric vector
#' @param k IQR multiplier (default 1.5)
#' @return logical vector, TRUE where outlier
detect_outliers <- function(x, k = 1.5) {
  q <- quantile(x, c(0.25, 0.75), na.rm = TRUE)
  iqr <- q[2] - q[1]
  x < (q[1] - k * iqr) | x > (q[2] + k * iqr)
}

#' Run Shapiro-Wilk normality test on simulation metric.
#' @param x numeric vector (n <= 5000)
#' @return list with statistic and p.value
normality_test <- function(x) {
  x_clean <- na.omit(x)
  if (length(x_clean) < 3) return(list(statistic = NA, p.value = NA))
  result <- shapiro.test(x_clean[seq_len(min(5000L, length(x_clean)))])
  list(statistic = as.numeric(result$statistic), p.value = result$p.value)
}

#' Analyze a data frame of Monte Carlo results.
#' @param df data.frame with numeric columns
#' @return list of per-column stats
analyze_mc_results <- function(df) {
  numeric_cols <- names(df)[sapply(df, is.numeric)]
  lapply(setNames(numeric_cols, numeric_cols), function(col) {
    x <- df[[col]]
    c(
      compute_stats(x),
      outlier_count = sum(detect_outliers(x)),
      normality     = normality_test(x)
    )
  })
}

#' Compare two experiment conditions using Wilcoxon rank-sum test.
#' @param a numeric vector (condition A)
#' @param b numeric vector (condition B)
#' @return list with p.value and effect size (rank-biserial r)
compare_conditions <- function(a, b) {
  test  <- wilcox.test(a, b, exact = FALSE)
  r     <- 1 - (2 * test$statistic) / (length(a) * length(b))
  list(p.value = test$p.value, effect_r = as.numeric(r))
}
