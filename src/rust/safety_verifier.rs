// Phase 652 — Rust Safety Verifier (formal safety property verification)
use std::collections::HashSet;

#[derive(Debug, Clone)]
pub struct DroneState {
    pub id: String,
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

pub struct SafetyVerifier {
    min_separation_m: f64,
    max_altitude_m: f64,
    geofence_radius_m: f64,
}

impl SafetyVerifier {
    pub fn new(min_sep: f64, max_alt: f64, radius: f64) -> Self {
        Self { min_separation_m: min_sep, max_altitude_m: max_alt, geofence_radius_m: radius }
    }

    pub fn verify_separation(&self, drones: &[DroneState]) -> Vec<(String, String)> {
        let mut violations = Vec::new();
        for i in 0..drones.len() {
            for j in i+1..drones.len() {
                let d = self.distance(&drones[i], &drones[j]);
                if d < self.min_separation_m {
                    violations.push((drones[i].id.clone(), drones[j].id.clone()));
                }
            }
        }
        violations
    }

    pub fn verify_altitude(&self, drones: &[DroneState]) -> Vec<String> {
        drones.iter().filter(|d| d.z > self.max_altitude_m || d.z < 0.0)
            .map(|d| d.id.clone()).collect()
    }

    fn distance(&self, a: &DroneState, b: &DroneState) -> f64 {
        ((a.x-b.x).powi(2) + (a.y-b.y).powi(2) + (a.z-b.z).powi(2)).sqrt()
    }
}
