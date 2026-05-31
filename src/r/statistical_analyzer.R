# statistical_analyzer.R - Statistical analysis for SDACS drone data
# R implementation of swarm behavior statistical analysis

library(stats)

# Drone state data frame structure
create_drone_df <- function(n = 10, seed = 42) {
  set.seed(seed)
  data.frame(
    id       = paste0("D-", sprintf("%03d", seq_len(n))),
    x        = runif(n, -500, 500),
    y        = runif(n, -500, 500),
    z        = runif(n, 20, 120),
    vx       = rnorm(n, 0, 5),
    vy       = rnorm(n, 0, 5),
    battery  = sample(10:100, n, replace = TRUE),
    status   = sample(c("active","idle","returning"), n, replace = TRUE)
  )
}

# Compute pairwise distances between all drones
pairwise_distances <- function(df) {
  n <- nrow(df)
  dist_matrix <- matrix(0, n, n)
  for (i in seq_len(n)) {
    for (j in seq_len(n)) {
      if (i != j) {
        dx <- df$x[i] - df$x[j]
        dy <- df$y[i] - df$y[j]
        dz <- df$z[i] - df$z[j]
        dist_matrix[i, j] <- sqrt(dx^2 + dy^2 + dz^2)
      }
    }
  }
  dist_matrix
}

# Statistical summary of swarm behavior
swarm_summary <- function(df) {
  speeds <- sqrt(df$vx^2 + df$vy^2)
  list(
    n_drones       = nrow(df),
    mean_battery   = mean(df$battery),
    sd_battery     = sd(df$battery),
    mean_altitude  = mean(df$z),
    mean_speed     = mean(speeds),
    active_count   = sum(df$status == "active"),
    battery_alert  = sum(df$battery < 20)
  )
}

# Main analysis
drones <- create_drone_df(20)
summary_stats <- swarm_summary(drones)
cat("SDACS Statistical Analyzer\n")
cat(sprintf("Drones: %d, Mean battery: %.1f%%\n",
            summary_stats$n_drones, summary_stats$mean_battery))
