/// Phase 322: Rust Satellite Link Engine
/// LEO orbit propagation, link budget calculation, handover management.
/// Safe concurrent access with Rust ownership model.

use std::collections::HashMap;
use std::f64::consts::PI;

#[derive(Debug, Clone)]
pub enum OrbitType {
    LEO,
    MEO,
    GEO,
}

#[derive(Debug, Clone, PartialEq)]
pub enum LinkStatus {
    Connected,
    Handover,
    Lost,
    Degraded,
}

#[derive(Debug, Clone)]
pub struct Vec3 {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Vec3 {
    pub fn new(x: f64, y: f64, z: f64) -> Self {
        Self { x, y, z }
    }

    pub fn distance(&self, other: &Vec3) -> f64 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        let dz = self.z - other.z;
        (dx * dx + dy * dy + dz * dz).sqrt()
    }
}

#[derive(Debug, Clone)]
pub struct Satellite {
    pub sat_id: String,
    pub orbit_type: OrbitType,
    pub altitude_km: f64,
    pub velocity_kms: f64,
    pub position: Vec3,
    pub is_active: bool,
}

impl Satellite {
    pub fn new_leo(sat_id: &str, alt_km: f64, lon_deg: f64) -> Self {
        let r = 6371.0 + alt_km;
        let lon_rad = lon_deg * PI / 180.0;
        Self {
            sat_id: sat_id.to_string(),
            orbit_type: OrbitType::LEO,
            altitude_km: alt_km,
            velocity_kms: 7.6,
            position: Vec3::new(r * lon_rad.cos(), r * lon_rad.sin(), 0.0),
            is_active: true,
        }
    }
}

#[derive(Debug, Clone)]
pub struct SatLink {
    pub satellite_id: String,
    pub drone_id: String,
    pub status: LinkStatus,
    pub snr_db: f64,
    pub latency_ms: f64,
    pub elevation_deg: f64,
}

#[derive(Debug)]
pub struct LinkBudget {
    pub tx_power_dbw: f64,
    pub tx_gain_dbi: f64,
    pub rx_gain_dbi: f64,
    pub freq_ghz: f64,
    pub path_loss_db: f64,
    pub snr_db: f64,
    pub available: bool,
}

pub struct SatelliteLinkEngine {
    satellites: HashMap<String, Satellite>,
    links: HashMap<String, SatLink>,
    handover_count: u32,
    min_elevation_deg: f64,
}

impl SatelliteLinkEngine {
    pub fn new() -> Self {
        Self {
            satellites: HashMap::new(),
            links: HashMap::new(),
            handover_count: 0,
            min_elevation_deg: 10.0,
        }
    }

    pub fn add_satellite(&mut self, sat: Satellite) {
        self.satellites.insert(sat.sat_id.clone(), sat);
    }

    pub fn propagate_orbits(&mut self, dt_sec: f64) {
        for sat in self.satellites.values_mut() {
            if !sat.is_active { continue; }
            let r = 6371.0 + sat.altitude_km;
            let omega = sat.velocity_kms / r;
            let angle = omega * dt_sec;
            let (cos_a, sin_a) = (angle.cos(), angle.sin());
            let (x, y) = (sat.position.x, sat.position.y);
            sat.position.x = x * cos_a - y * sin_a;
            sat.position.y = x * sin_a + y * cos_a;
        }
    }

    pub fn compute_link_budget(&self, sat: &Satellite, drone_pos: &Vec3) -> LinkBudget {
        let slant_range = sat.position.distance(drone_pos);
        let fspl = if slant_range > 0.0 {
            20.0 * slant_range.log10() + 20.0 * 12.0_f64.log10() + 92.45
        } else {
            0.0
        };
        let snr = 10.0 + 5.0 + 30.0 - fspl - 2.0 - 3.0;
        LinkBudget {
            tx_power_dbw: 10.0,
            tx_gain_dbi: 5.0,
            rx_gain_dbi: 30.0,
            freq_ghz: 12.0,
            path_loss_db: fspl,
            snr_db: snr,
            available: snr > 5.0,
        }
    }

    pub fn compute_latency(&self, sat: &Satellite, drone_pos: &Vec3) -> f64 {
        let dist = sat.position.distance(drone_pos);
        dist / 299792.458 * 1000.0  // ms
    }

    pub fn find_best_satellite(&self, drone_pos: &Vec3) -> Option<&str> {
        let mut best_sat: Option<&str> = None;
        let mut best_snr = f64::NEG_INFINITY;
        for sat in self.satellites.values() {
            if !sat.is_active { continue; }
            let budget = self.compute_link_budget(sat, drone_pos);
            if budget.snr_db > best_snr {
                best_snr = budget.snr_db;
                best_sat = Some(&sat.sat_id);
            }
        }
        best_sat
    }

    pub fn update_link(&mut self, drone_id: &str, drone_pos: &Vec3) -> Option<SatLink> {
        let best_id = self.find_best_satellite(drone_pos)?.to_string();
        let sat = self.satellites.get(&best_id)?;

        if let Some(current) = self.links.get(drone_id) {
            if current.satellite_id != best_id {
                self.handover_count += 1;
            }
        }

        let budget = self.compute_link_budget(sat, drone_pos);
        let latency = self.compute_latency(sat, drone_pos);
        let status = if budget.available { LinkStatus::Connected } else { LinkStatus::Degraded };

        let link = SatLink {
            satellite_id: best_id,
            drone_id: drone_id.to_string(),
            status,
            snr_db: budget.snr_db,
            latency_ms: latency,
            elevation_deg: 0.0,
        };
        self.links.insert(drone_id.to_string(), link.clone());
        Some(link)
    }

    pub fn summary(&self) -> String {
        let connected = self.links.values().filter(|l| l.status == LinkStatus::Connected).count();
        format!(
            "Satellites: {} | Links: {} | Connected: {} | Handovers: {}",
            self.satellites.len(), self.links.len(), connected, self.handover_count
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_satellite() {
        let mut engine = SatelliteLinkEngine::new();
        engine.add_satellite(Satellite::new_leo("s1", 550.0, 0.0));
        assert_eq!(engine.satellites.len(), 1);
    }

    #[test]
    fn test_link_budget() {
        let mut engine = SatelliteLinkEngine::new();
        let sat = Satellite::new_leo("s1", 550.0, 0.0);
        engine.add_satellite(sat.clone());
        let budget = engine.compute_link_budget(&sat, &Vec3::new(6371.0, 0.0, 0.0));
        assert!(budget.path_loss_db > 0.0);
    }

    #[test]
    fn test_update_link() {
        let mut engine = SatelliteLinkEngine::new();
        engine.add_satellite(Satellite::new_leo("s1", 550.0, 0.0));
        let link = engine.update_link("d1", &Vec3::new(6371.0, 0.0, 0.0));
        assert!(link.is_some());
    }
}
