//! SDACS weather risk model (Rust).
//! Keeps parity with Python canonical formula.

#[derive(Debug, Clone, Copy)]
pub struct WeatherRiskInput {
    pub wind_mps: f64,
    pub visibility_km: f64,
    pub precipitation_level: f64,
    pub congestion: f64,
}

#[derive(Debug, Clone)]
pub struct WeatherRiskOutput {
    pub score: f64,
    pub category: &'static str,
}

fn clamp(v: f64, lo: f64, hi: f64) -> f64 {
    if v < lo {
        lo
    } else if v > hi {
        hi
    } else {
        v
    }
}

pub fn compute_weather_risk(input: WeatherRiskInput) -> WeatherRiskOutput {
    let wind_norm = clamp(input.wind_mps / 20.0, 0.0, 1.0);
    let vis_norm = clamp(input.visibility_km / 10.0, 0.0, 1.0);
    let vis_penalty = 1.0 - vis_norm;
    let precip = clamp(input.precipitation_level, 0.0, 1.0);
    let congestion = clamp(input.congestion, 0.0, 1.0);

    let raw = 0.35 * wind_norm + 0.25 * vis_penalty + 0.20 * precip + 0.20 * congestion;
    let score = (clamp(raw, 0.0, 1.0) * 10000.0).round() / 10000.0;

    let category = if score < 0.25 {
        "GREEN"
    } else if score < 0.50 {
        "YELLOW"
    } else if score < 0.75 {
        "ORANGE"
    } else {
        "RED"
    };

    WeatherRiskOutput { score, category }
}
