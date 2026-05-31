# SDACS Phase 617 — R statistical analysis of swarm simulation results
analyze_simulation <- function(results_df) {
  summary_stats <- list(
    mean_nmr = mean(results_df$nmr, na.rm = TRUE),
    sd_nmr = sd(results_df$nmr, na.rm = TRUE),
    mean_pe = mean(results_df$pe, na.rm = TRUE),
    collision_rate = sum(results_df$collisions) / nrow(results_df)
  )
  return(summary_stats)
}
