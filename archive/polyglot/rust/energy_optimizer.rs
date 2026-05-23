/// Phase 308: Rust Energy Harvest Optimizer
/// Solar/Wind/RF energy harvest simulation with ownership semantics.
/// Zero-cost abstractions for real-time energy management.

use std::collections::HashMap;
use std::f64::consts::PI;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum HarvestSource {
    Solar,
    Wind,
    RF,
    Thermal,
}

#[derive(Debug, Clone)]
pub struct EnergyState {
    pub drone_id: String,
    pub battery_wh: f64,
    pub capacity_wh: f64,
    pub consumption_rate_w: f64,
    pub harvest_rates: HashMap<HarvestSource, f64>,
    pub soc_pct: f64,
}

impl EnergyState {
    pub fn new(drone_id: &str, capacity_wh: f64) -> Self {
        Self {
            drone_id: drone_id.to_string(),
            battery_wh: capacity_wh,
            capacity_wh,
            consumption_rate_w: 50.0,
            harvest_rates: HashMap::new(),
            soc_pct: 100.0,
        }
    }

    pub fn update_soc(&mut self) {
        self.soc_pct = (self.battery_wh / self.capacity_wh) * 100.0;
    }
}

#[derive(Debug, Clone)]
pub struct SolarModel {
    pub panel_area_m2: f64,
    pub efficiency: f64,
    pub irradiance_base: f64,
}

impl SolarModel {
    pub fn new(panel_area: f64, efficiency: f64) -> Self {
        Self {
            panel_area_m2: panel_area,
            efficiency,
            irradiance_base: 1000.0, // W/m² at peak
        }
    }

    /// Calculate solar harvest based on time of day (0-24h) and cloud cover (0-1)
    pub fn harvest_power(&self, hour: f64, cloud_cover: f64) -> f64 {
        let sun_angle = PI * (hour - 6.0) / 12.0; // peak at noon
        let sun_factor = if hour >= 6.0 && hour <= 18.0 {
            sun_angle.sin().max(0.0)
        } else {
            0.0
        };
        let cloud_factor = 1.0 - cloud_cover * 0.8;
        self.irradiance_base * self.panel_area_m2 * self.efficiency * sun_factor * cloud_factor
    }
}

#[derive(Debug, Clone)]
pub struct WindModel {
    pub turbine_radius_m: f64,
    pub efficiency: f64,
    pub air_density: f64,
}

impl WindModel {
    pub fn new(radius: f64, efficiency: f64) -> Self {
        Self {
            turbine_radius_m: radius,
            efficiency,
            air_density: 1.225,
        }
    }

    /// P = 0.5 * rho * A * v³ * Cp
    pub fn harvest_power(&self, wind_speed_ms: f64) -> f64 {
        let area = PI * self.turbine_radius_m.powi(2);
        0.5 * self.air_density * area * wind_speed_ms.powi(3) * self.efficiency
    }
}

pub struct EnergyHarvestOptimizer {
    pub drones: HashMap<String, EnergyState>,
    solar: SolarModel,
    wind: WindModel,
    step_count: u64,
    total_harvested_wh: f64,
    total_consumed_wh: f64,
}

impl EnergyHarvestOptimizer {
    pub fn new() -> Self {
        Self {
            drones: HashMap::new(),
            solar: SolarModel::new(0.1, 0.22),
            wind: WindModel::new(0.05, 0.35),
            step_count: 0,
            total_harvested_wh: 0.0,
            total_consumed_wh: 0.0,
        }
    }

    pub fn add_drone(&mut self, drone_id: &str, capacity_wh: f64) {
        self.drones.insert(drone_id.to_string(), EnergyState::new(drone_id, capacity_wh));
    }

    pub fn step(&mut self, dt_sec: f64, hour: f64, wind_speed: f64, cloud_cover: f64) {
        let solar_power = self.solar.harvest_power(hour, cloud_cover);
        let wind_power = self.wind.harvest_power(wind_speed);

        for state in self.drones.values_mut() {
            let harvest_wh = (solar_power + wind_power) * dt_sec / 3600.0;
            let consumed_wh = state.consumption_rate_w * dt_sec / 3600.0;

            state.battery_wh = (state.battery_wh + harvest_wh - consumed_wh)
                .max(0.0)
                .min(state.capacity_wh);
            state.harvest_rates.insert(HarvestSource::Solar, solar_power);
            state.harvest_rates.insert(HarvestSource::Wind, wind_power);
            state.update_soc();

            self.total_harvested_wh += harvest_wh;
            self.total_consumed_wh += consumed_wh;
        }
        self.step_count += 1;
    }

    pub fn get_critical_drones(&self, threshold_pct: f64) -> Vec<&str> {
        self.drones.iter()
            .filter(|(_, s)| s.soc_pct < threshold_pct)
            .map(|(id, _)| id.as_str())
            .collect()
    }

    pub fn summary(&self) -> String {
        let avg_soc: f64 = if self.drones.is_empty() {
            0.0
        } else {
            self.drones.values().map(|s| s.soc_pct).sum::<f64>() / self.drones.len() as f64
        };
        format!(
            "Drones: {} | Steps: {} | AvgSoC: {:.1}% | Harvested: {:.2} Wh | Consumed: {:.2} Wh",
            self.drones.len(), self.step_count, avg_soc,
            self.total_harvested_wh, self.total_consumed_wh
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_solar_noon_peak() {
        let solar = SolarModel::new(0.1, 0.22);
        let power = solar.harvest_power(12.0, 0.0);
        assert!(power > 0.0);
        assert!(power <= 1000.0 * 0.1 * 0.22 + 1.0);
    }

    #[test]
    fn test_solar_night_zero() {
        let solar = SolarModel::new(0.1, 0.22);
        let power = solar.harvest_power(2.0, 0.0);
        assert_eq!(power, 0.0);
    }

    #[test]
    fn test_wind_power() {
        let wind = WindModel::new(0.05, 0.35);
        let power = wind.harvest_power(5.0);
        assert!(power > 0.0);
    }

    #[test]
    fn test_optimizer_step() {
        let mut opt = EnergyHarvestOptimizer::new();
        opt.add_drone("d1", 100.0);
        opt.step(1.0, 12.0, 5.0, 0.2);
        assert!(opt.drones["d1"].soc_pct <= 100.0);
        assert_eq!(opt.step_count, 1);
    }

    #[test]
    fn test_critical_detection() {
        let mut opt = EnergyHarvestOptimizer::new();
        opt.add_drone("d1", 100.0);
        // Drain battery
        opt.drones.get_mut("d1").unwrap().battery_wh = 10.0;
        opt.drones.get_mut("d1").unwrap().update_soc();
        let critical = opt.get_critical_drones(20.0);
        assert_eq!(critical.len(), 1);
    }
}
