// Phase 642: Safety Verifier — Rust
// SDACS formal safety property checker for drone mission plans

use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct DroneState {
    pub id:       String,
    pub altitude: f64,
    pub battery:  f64,
    pub speed:    f64,
    pub mode:     String,
    pub lat:      f64,
    pub lon:      f64,
}

#[derive(Debug, Clone, PartialEq)]
pub enum SafetyResult {
    Safe,
    Violation { property: String, message: String, severity: u8 },
}

pub trait SafetyProperty {
    fn name(&self) -> &str;
    fn check(&self, state: &DroneState) -> SafetyResult;
}

pub struct AltitudeLimit { pub max_alt: f64 }
impl SafetyProperty for AltitudeLimit {
    fn name(&self) -> &str { "altitude_limit" }
    fn check(&self, s: &DroneState) -> SafetyResult {
        if s.altitude > self.max_alt {
            SafetyResult::Violation {
                property: self.name().into(),
                message:  format!("Altitude {:.1}m exceeds limit {:.1}m", s.altitude, self.max_alt),
                severity: 2,
            }
        } else { SafetyResult::Safe }
    }
}

pub struct BatteryLimit { pub critical: f64 }
impl SafetyProperty for BatteryLimit {
    fn name(&self) -> &str { "battery_critical" }
    fn check(&self, s: &DroneState) -> SafetyResult {
        if s.battery < self.critical {
            SafetyResult::Violation {
                property: self.name().into(),
                message:  format!("Battery {:.1}% below critical {:.1}%", s.battery, self.critical),
                severity: 3,
            }
        } else { SafetyResult::Safe }
    }
}

pub struct SafetyVerifier {
    properties: Vec<Box<dyn SafetyProperty>>,
}

impl SafetyVerifier {
    pub fn new() -> Self { Self { properties: Vec::new() } }
    pub fn add<P: SafetyProperty + 'static>(&mut self, prop: P) { self.properties.push(Box::new(prop)); }
    pub fn verify(&self, state: &DroneState) -> Vec<SafetyResult> {
        self.properties.iter()
            .map(|p| p.check(state))
            .filter(|r| *r != SafetyResult::Safe)
            .collect()
    }
    pub fn is_safe(&self, state: &DroneState) -> bool { self.verify(state).is_empty() }
}

fn main() {
    let mut verifier = SafetyVerifier::new();
    verifier.add(AltitudeLimit { max_alt: 120.0 });
    verifier.add(BatteryLimit { critical: 10.0 });

    let state = DroneState { id: "D001".into(), altitude: 60.0, battery: 85.0,
        speed: 10.0, mode: "AUTO".into(), lat: 37.5665, lon: 126.978 };
    let violations = verifier.verify(&state);
    println!("Phase 642: Safety verified — {} violations", violations.len());
}
