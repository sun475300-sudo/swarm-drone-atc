// safety_verifier.rs - Safety verification for SDACS drone system
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct DroneState {
    pub id:       String,
    pub x:        f64,
    pub y:        f64,
    pub z:        f64,
    pub battery:  u8,
    pub status:   String,
}

#[derive(Debug, PartialEq)]
pub enum SafetyCode { Ok, AltitudeViolation, BatteryLow, SeparationViolation }

#[derive(Debug)]
pub struct SafetyResult {
    pub drone_id: String,
    pub code:     SafetyCode,
    pub message:  String,
}

pub struct SafetyVerifier {
    pub min_separation: f64,
    pub max_altitude:   f64,
    pub min_battery:    u8,
}

impl SafetyVerifier {
    pub fn new() -> Self {
        SafetyVerifier { min_separation: 30.0, max_altitude: 400.0, min_battery: 10 }
    }

    pub fn verify_drone(&self, d: &DroneState) -> SafetyResult {
        if d.z > self.max_altitude {
            return SafetyResult { drone_id: d.id.clone(), code: SafetyCode::AltitudeViolation,
                                  message: format!("Altitude {:.1}m exceeds maximum", d.z) };
        }
        if d.battery < self.min_battery {
            return SafetyResult { drone_id: d.id.clone(), code: SafetyCode::BatteryLow,
                                  message: format!("Battery {}% below minimum", d.battery) };
        }
        SafetyResult { drone_id: d.id.clone(), code: SafetyCode::Ok, message: "OK".into() }
    }

    pub fn verify_separation(&self, drones: &[DroneState]) -> Vec<(String, String, f64)> {
        let mut violations = Vec::new();
        for i in 0..drones.len() {
            for j in i+1..drones.len() {
                let a = &drones[i]; let b = &drones[j];
                let dist = ((a.x-b.x).powi(2) + (a.y-b.y).powi(2) + (a.z-b.z).powi(2)).sqrt();
                if dist < self.min_separation {
                    violations.push((a.id.clone(), b.id.clone(), dist));
                }
            }
        }
        violations
    }
}
