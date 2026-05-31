// Phase 652 — Safety Property Verifier in Rust
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct DroneState {
    pub id: String,
    pub pos: [f64; 3],
    pub vel: [f64; 3],
}

#[derive(Debug, PartialEq)]
pub enum SafetyResult { Safe, Violation(String) }

pub struct SafetyVerifier {
    pub min_separation: f64,
    pub max_altitude: f64,
    pub geofence: [f64; 4],  // [xmin, xmax, ymin, ymax]
}

impl SafetyVerifier {
    pub fn verify(&self, drones: &[DroneState]) -> Vec<SafetyResult> {
        let mut results = Vec::new();
        for (i, a) in drones.iter().enumerate() {
            for b in &drones[i+1..] {
                let d = dist(&a.pos, &b.pos);
                if d < self.min_separation {
                    results.push(SafetyResult::Violation(
                        format!("separation {:.2}m < {:.2}m ({} <-> {})", d, self.min_separation, a.id, b.id)
                    ));
                }
            }
            if a.pos[2] > self.max_altitude {
                results.push(SafetyResult::Violation(format!("{} altitude {:.1}m exceeds max", a.id, a.pos[2])));
            }
        }
        results
    }
}

fn dist(a: &[f64; 3], b: &[f64; 3]) -> f64 {
    ((a[0]-b[0]).powi(2) + (a[1]-b[1]).powi(2) + (a[2]-b[2]).powi(2)).sqrt()
}
