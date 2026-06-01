// Phase 642: Safety Verifier — 드론 안전 검증 모듈 (Rust)
// Formal safety property checking for swarm drone operations.

use std::collections::HashMap;

/// SafetyProperty describes a verifiable system property.
#[derive(Debug, Clone)]
pub struct SafetyProperty {
    pub name: String,
    pub description: String,
    pub critical: bool,
}

/// DroneState snapshot for verification.
#[derive(Debug, Clone)]
pub struct DroneState {
    pub id: usize,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub battery: f64,
    pub velocity: f64,
    pub armed: bool,
}

/// VerificationResult holds the outcome of a single property check.
#[derive(Debug)]
pub struct VerificationResult {
    pub property: String,
    pub passed: bool,
    pub violations: Vec<String>,
}

/// SafetyVerifier checks a fleet snapshot against formal safety invariants.
pub struct SafetyVerifier {
    pub properties: Vec<SafetyProperty>,
    pub min_altitude: f64,
    pub max_velocity: f64,
    pub min_separation: f64,
    pub min_battery: f64,
}

impl SafetyVerifier {
    /// Creates a verifier with default aviation safety parameters.
    pub fn new() -> Self {
        let props = vec![
            SafetyProperty { name: "altitude_floor".into(), description: "Drones must stay above 10m AGL".into(), critical: true },
            SafetyProperty { name: "velocity_cap".into(), description: "Velocity must not exceed 30 m/s".into(), critical: true },
            SafetyProperty { name: "separation".into(), description: "Minimum 5m separation between drones".into(), critical: true },
            SafetyProperty { name: "battery_reserve".into(), description: "Battery must stay above 10%".into(), critical: false },
        ];
        SafetyVerifier {
            properties: props,
            min_altitude: 10.0,
            max_velocity: 30.0,
            min_separation: 5.0,
            min_battery: 10.0,
        }
    }

    /// Verifies all properties against a drone fleet snapshot.
    pub fn verify_all(&self, fleet: &[DroneState]) -> Vec<VerificationResult> {
        vec![
            self.check_altitude(fleet),
            self.check_velocity(fleet),
            self.check_separation(fleet),
            self.check_battery(fleet),
        ]
    }

    fn check_altitude(&self, fleet: &[DroneState]) -> VerificationResult {
        let violations: Vec<String> = fleet.iter()
            .filter(|d| d.z < self.min_altitude)
            .map(|d| format!("drone_{} altitude {:.1}m below floor", d.id, d.z))
            .collect();
        VerificationResult { property: "altitude_floor".into(), passed: violations.is_empty(), violations }
    }

    fn check_velocity(&self, fleet: &[DroneState]) -> VerificationResult {
        let violations: Vec<String> = fleet.iter()
            .filter(|d| d.velocity > self.max_velocity)
            .map(|d| format!("drone_{} velocity {:.1} m/s exceeds cap", d.id, d.velocity))
            .collect();
        VerificationResult { property: "velocity_cap".into(), passed: violations.is_empty(), violations }
    }

    fn check_separation(&self, fleet: &[DroneState]) -> VerificationResult {
        let mut violations = Vec::new();
        for i in 0..fleet.len() {
            for j in (i+1)..fleet.len() {
                let dx = fleet[i].x - fleet[j].x;
                let dy = fleet[i].y - fleet[j].y;
                let dz = fleet[i].z - fleet[j].z;
                let dist = (dx*dx + dy*dy + dz*dz).sqrt();
                if dist < self.min_separation {
                    violations.push(format!("drone_{} and drone_{} too close: {:.2}m", fleet[i].id, fleet[j].id, dist));
                }
            }
        }
        VerificationResult { property: "separation".into(), passed: violations.is_empty(), violations }
    }

    fn check_battery(&self, fleet: &[DroneState]) -> VerificationResult {
        let violations: Vec<String> = fleet.iter()
            .filter(|d| d.battery < self.min_battery)
            .map(|d| format!("drone_{} battery {:.1}% critical", d.id, d.battery))
            .collect();
        VerificationResult { property: "battery_reserve".into(), passed: violations.is_empty(), violations }
    }

    /// Returns a summary statistics map.
    pub fn summary(&self, results: &[VerificationResult]) -> HashMap<String, usize> {
        let mut m = HashMap::new();
        m.insert("total_checks".into(), results.len());
        m.insert("passed".into(), results.iter().filter(|r| r.passed).count());
        m.insert("failed".into(), results.iter().filter(|r| !r.passed).count());
        m
    }
}

fn main() {
    println!("Phase 642: Safety Verifier — 드론 안전성 공식 검증");
    let verifier = SafetyVerifier::new();
    let fleet = vec![
        DroneState { id: 0, x: 0.0, y: 0.0, z: 50.0, battery: 75.0, velocity: 10.0, armed: true },
        DroneState { id: 1, x: 10.0, y: 10.0, z: 55.0, battery: 60.0, velocity: 8.0, armed: true },
        DroneState { id: 2, x: 5.0, y: 5.0, z: 8.0, battery: 5.0, velocity: 35.0, armed: true },
    ];
    let results = verifier.verify_all(&fleet);
    let summary = verifier.summary(&results);
    println!("Verification summary: {:?}", summary);
}
