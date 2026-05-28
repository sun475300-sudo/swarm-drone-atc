/**
 * SDACS weather risk model (C++).
 * Formula parity with simulation/weather_risk_model.py
 */

#include <algorithm>
#include <cmath>
#include <string>

struct WeatherRiskInput {
    double wind_mps;
    double visibility_km;
    double precipitation_level;
    double congestion;
};

struct WeatherRiskOutput {
    double score;
    std::string category;
};

static double clamp(double v, double lo, double hi) {
    return std::max(lo, std::min(hi, v));
}

WeatherRiskOutput compute_weather_risk(const WeatherRiskInput& input) {
    const double wind_norm = clamp(input.wind_mps / 20.0, 0.0, 1.0);
    const double vis_norm = clamp(input.visibility_km / 10.0, 0.0, 1.0);
    const double vis_penalty = 1.0 - vis_norm;
    const double precip = clamp(input.precipitation_level, 0.0, 1.0);
    const double congestion = clamp(input.congestion, 0.0, 1.0);

    const double raw = 0.35 * wind_norm + 0.25 * vis_penalty + 0.20 * precip + 0.20 * congestion;
    const double score = std::round(clamp(raw, 0.0, 1.0) * 10000.0) / 10000.0;

    std::string category = "RED";
    if (score < 0.25) {
        category = "GREEN";
    } else if (score < 0.50) {
        category = "YELLOW";
    } else if (score < 0.75) {
        category = "ORANGE";
    }

    return {score, category};
}
