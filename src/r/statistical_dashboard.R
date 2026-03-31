# Phase 557: R Statistical Analysis Dashboard
# 통계 분석: 드론 성능 지표 분석, 분포 적합, 이상치 탐지, 요약 통계

# PRNG
prng_new <- function(seed) {
  state <- bitwXor(as.integer(seed), as.integer(0x6c62272e))
  list(state = state)
}

prng_next <- function(rng) {
  s <- rng$state
  s <- bitwXor(s, bitwShiftL(s, 13L))
  s <- bitwXor(s, bitwShiftR(s, 7L))
  s <- bitwXor(s, bitwShiftL(s, 17L))
  rng$state <- s
  list(val = abs(s), rng = rng)
}

prng_uniform <- function(rng) {
  r <- prng_next(rng)
  list(val = (r$val %% 10000L) / 10000.0, rng = r$rng)
}

# Generate drone telemetry data
generate_telemetry <- function(n_drones, n_steps, seed = 42) {
  rng <- prng_new(seed)
  data <- data.frame(
    drone_id = character(),
    step = integer(),
    altitude = numeric(),
    speed = numeric(),
    battery = numeric(),
    temperature = numeric(),
    stringsAsFactors = FALSE
  )

  for (i in seq_len(n_drones)) {
    battery <- 100
    for (t in seq_len(n_steps)) {
      r1 <- prng_uniform(rng); rng <- r1$rng
      r2 <- prng_uniform(rng); rng <- r2$rng
      r3 <- prng_uniform(rng); rng <- r3$rng
      r4 <- prng_uniform(rng); rng <- r4$rng

      altitude <- 30 + r1$val * 70
      speed <- r2$val * 25
      battery <- max(0, battery - r3$val * 2)
      temperature <- 20 + r4$val * 40

      data <- rbind(data, data.frame(
        drone_id = paste0("drone_", i - 1),
        step = t,
        altitude = altitude,
        speed = speed,
        battery = battery,
        temperature = temperature,
        stringsAsFactors = FALSE
      ))
    }
  }
  data
}

# Statistical analysis functions
compute_summary_stats <- function(data) {
  metrics <- c("altitude", "speed", "battery", "temperature")
  results <- list()
  for (m in metrics) {
    vals <- data[[m]]
    results[[m]] <- list(
      mean = mean(vals),
      sd = sd(vals),
      median = median(vals),
      min = min(vals),
      max = max(vals),
      q25 = quantile(vals, 0.25, names = FALSE),
      q75 = quantile(vals, 0.75, names = FALSE)
    )
  }
  results
}

detect_outliers <- function(data, column, k = 1.5) {
  vals <- data[[column]]
  q1 <- quantile(vals, 0.25, names = FALSE)
  q3 <- quantile(vals, 0.75, names = FALSE)
  iqr <- q3 - q1
  lower <- q1 - k * iqr
  upper <- q3 + k * iqr
  outliers <- data[vals < lower | vals > upper, ]
  list(n_outliers = nrow(outliers), lower = lower, upper = upper)
}

per_drone_stats <- function(data) {
  drones <- unique(data$drone_id)
  results <- data.frame(
    drone_id = character(),
    avg_altitude = numeric(),
    avg_speed = numeric(),
    min_battery = numeric(),
    max_temp = numeric(),
    stringsAsFactors = FALSE
  )
  for (d in drones) {
    dd <- data[data$drone_id == d, ]
    results <- rbind(results, data.frame(
      drone_id = d,
      avg_altitude = mean(dd$altitude),
      avg_speed = mean(dd$speed),
      min_battery = min(dd$battery),
      max_temp = max(dd$temperature),
      stringsAsFactors = FALSE
    ))
  }
  results
}

# Main
main <- function() {
  cat("Generating telemetry data...\n")
  data <- generate_telemetry(10, 50, 42)
  cat(sprintf("Records: %d\n", nrow(data)))

  stats <- compute_summary_stats(data)
  cat(sprintf("Altitude — mean: %.1f, sd: %.1f\n", stats$altitude$mean, stats$altitude$sd))
  cat(sprintf("Speed — mean: %.1f, sd: %.1f\n", stats$speed$mean, stats$speed$sd))
  cat(sprintf("Battery — mean: %.1f, min: %.1f\n", stats$battery$mean, stats$battery$min))

  outliers <- detect_outliers(data, "temperature")
  cat(sprintf("Temperature outliers: %d\n", outliers$n_outliers))

  drone_stats <- per_drone_stats(data)
  cat(sprintf("Drones analyzed: %d\n", nrow(drone_stats)))
}

main()
