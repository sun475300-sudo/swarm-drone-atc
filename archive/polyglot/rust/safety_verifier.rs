// Phase 652: Safety Verifier — Rust Formal Safety Property Checker
// 형식 안전 검증기: 분리간격, 고도제한, 배터리 임계치 등 안전 속성 검증

use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct DroneState {
    pub drone_id: String,
    pub position: [f64; 3],
    pub velocity: [f64; 3],
    pub battery_pct: f64,
    pub altitude_m: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub enum SafetyLevel {
    Safe,
    Warning,
    Critical,
    Violation,
}

#[derive(Debug, Clone)]
pub struct SafetyProperty {
    pub name: String,
    pub description: String,
    pub threshold: f64,
}

#[derive(Debug)]
pub struct VerificationResult {
    pub property: String,
    pub level: SafetyLevel,
    pub value: f64,
    pub message: String,
}

pub struct SafetyVerifier {
    properties: Vec<SafetyProperty>,
    min_separation_m: f64,
    max_altitude_m: f64,
    min_altitude_m: f64,
    min_battery_pct: f64,
    max_speed_ms: f64,
}

impl SafetyVerifier {
    pub fn new() -> Self {
        let properties = vec![
            SafetyProperty {
                name: "MIN_SEPARATION".into(),
                description: "Minimum horizontal separation between drones".into(),
                threshold: 30.0,
            },
            SafetyProperty {
                name: "MAX_ALTITUDE".into(),
                description: "Maximum operating altitude".into(),
                threshold: 120.0,
            },
            SafetyProperty {
                name: "MIN_BATTERY".into(),
                description: "Minimum battery for continued flight".into(),
                threshold: 15.0,
            },
            SafetyProperty {
                name: "MAX_SPEED".into(),
                description: "Maximum allowable speed".into(),
                threshold: 25.0,
            },
        ];

        SafetyVerifier {
            properties,
            min_separation_m: 30.0,
            max_altitude_m: 120.0,
            min_altitude_m: 30.0,
            min_battery_pct: 15.0,
            max_speed_ms: 25.0,
        }
    }

    pub fn verify_separation(&self, drones: &[DroneState]) -> Vec<VerificationResult> {
        let mut results = Vec::new();
        for i in 0..drones.len() {
            for j in (i + 1)..drones.len() {
                let dx = drones[i].position[0] - drones[j].position[0];
                let dy = drones[i].position[1] - drones[j].position[1];
                let dist = (dx * dx + dy * dy).sqrt();

                let level = if dist < self.min_separation_m * 0.5 {
                    SafetyLevel::Violation
                } else if dist < self.min_separation_m {
                    SafetyLevel::Critical
                } else if dist < self.min_separation_m * 1.5 {
                    SafetyLevel::Warning
                } else {
                    SafetyLevel::Safe
                };

                results.push(VerificationResult {
                    property: "MIN_SEPARATION".into(),
                    level,
                    value: dist,
                    message: format!(
                        "{} <-> {}: {:.1}m",
                        drones[i].drone_id, drones[j].drone_id, dist
                    ),
                });
            }
        }
        results
    }

    pub fn verify_altitude(&self, drone: &DroneState) -> VerificationResult {
        let level = if drone.altitude_m > self.max_altitude_m {
            SafetyLevel::Violation
        } else if drone.altitude_m < self.min_altitude_m {
            SafetyLevel::Warning
        } else {
            SafetyLevel::Safe
        };

        VerificationResult {
            property: "ALTITUDE_BOUNDS".into(),
            level,
            value: drone.altitude_m,
            message: format!("{}: {:.1}m", drone.drone_id, drone.altitude_m),
        }
    }

    pub fn verify_battery(&self, drone: &DroneState) -> VerificationResult {
        let level = if drone.battery_pct < self.min_battery_pct * 0.5 {
            SafetyLevel::Violation
        } else if drone.battery_pct < self.min_battery_pct {
            SafetyLevel::Critical
        } else if drone.battery_pct < self.min_battery_pct * 2.0 {
            SafetyLevel::Warning
        } else {
            SafetyLevel::Safe
        };

        VerificationResult {
            property: "MIN_BATTERY".into(),
            level,
            value: drone.battery_pct,
            message: format!("{}: {:.1}%", drone.drone_id, drone.battery_pct),
        }
    }

    pub fn verify_speed(&self, drone: &DroneState) -> VerificationResult {
        let speed = (drone.velocity[0].powi(2)
            + drone.velocity[1].powi(2)
            + drone.velocity[2].powi(2))
        .sqrt();

        let level = if speed > self.max_speed_ms * 1.2 {
            SafetyLevel::Violation
        } else if speed > self.max_speed_ms {
            SafetyLevel::Critical
        } else {
            SafetyLevel::Safe
        };

        VerificationResult {
            property: "MAX_SPEED".into(),
            level,
            value: speed,
            message: format!("{}: {:.1} m/s", drone.drone_id, speed),
        }
    }

    pub fn verify_all(&self, drones: &[DroneState]) -> HashMap<String, Vec<VerificationResult>> {
        let mut all_results: HashMap<String, Vec<VerificationResult>> = HashMap::new();

        all_results.insert("separation".into(), self.verify_separation(drones));

        let mut alt_results = Vec::new();
        let mut bat_results = Vec::new();
        let mut spd_results = Vec::new();

        for d in drones {
            alt_results.push(self.verify_altitude(d));
            bat_results.push(self.verify_battery(d));
            spd_results.push(self.verify_speed(d));
        }

        all_results.insert("altitude".into(), alt_results);
        all_results.insert("battery".into(), bat_results);
        all_results.insert("speed".into(), spd_results);

        all_results
    }
}

fn main() {
    let verifier = SafetyVerifier::new();
    let drones = vec![
        DroneState {
            drone_id: "D-0001".into(),
            position: [0.0, 0.0, 60.0],
            velocity: [5.0, 0.0, 0.0],
            battery_pct: 85.0,
            altitude_m: 60.0,
        },
        DroneState {
            drone_id: "D-0002".into(),
            position: [25.0, 0.0, 60.0],
            velocity: [-5.0, 0.0, 0.0],
            battery_pct: 12.0,
            altitude_m: 60.0,
        },
    ];

    let results = verifier.verify_all(&drones);
    for (category, checks) in &results {
        println!("  [{}]", category);
        for r in checks {
            println!("    {:?} — {}", r.level, r.message);
        }
    }
}
