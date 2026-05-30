// SDACS Safety Verifier — Rust
// 군집드론 안전성 검증 모듈

use std::collections::HashMap;

/// 드론 상태 구조체
#[derive(Debug, Clone)]
pub struct DroneState {
    pub id: String,
    pub lat: f64,
    pub lon: f64,
    pub alt: f64,
    pub battery: u8,
    pub active: bool,
}

/// 안전 검증 결과
#[derive(Debug)]
pub enum VerificationResult {
    Safe,
    Warning(String),
    Critical(String),
}

/// 안전성 검증기
pub struct SafetyVerifier {
    min_separation: f64,
    max_altitude: f64,
    min_battery: u8,
}

impl SafetyVerifier {
    pub fn new(min_separation: f64, max_altitude: f64, min_battery: u8) -> Self {
        SafetyVerifier { min_separation, max_altitude, min_battery }
    }

    pub fn verify_drone(&self, drone: &DroneState) -> VerificationResult {
        if drone.battery <= self.min_battery {
            return VerificationResult::Critical(
                format!("Drone {} battery critical: {}%", drone.id, drone.battery)
            );
        }
        if drone.alt > self.max_altitude {
            return VerificationResult::Warning(
                format!("Drone {} exceeds max altitude: {:.1}m", drone.id, drone.alt)
            );
        }
        VerificationResult::Safe
    }

    pub fn verify_fleet(&self, drones: &[DroneState]) -> Vec<(String, VerificationResult)> {
        drones.iter()
            .map(|d| (d.id.clone(), self.verify_drone(d)))
            .collect()
    }
}

fn main() {
    let verifier = SafetyVerifier::new(5.0, 400.0, 20);
    let drones = vec![
        DroneState { id: "DRONE-001".into(), lat: 37.5665, lon: 126.978, alt: 100.0, battery: 85, active: true },
        DroneState { id: "DRONE-002".into(), lat: 37.5670, lon: 126.979, alt: 410.0, battery: 90, active: true },
    ];
    let results = verifier.verify_fleet(&drones);
    for (id, result) in results {
        println!("{}: {:?}", id, result);
    }
}
