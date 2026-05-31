// Safety Verifier — SDACS Phase 652
#![allow(dead_code)]
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct DroneState {
    pub id: String,
    pub lat: f64,
    pub lon: f64,
    pub alt: f64,
}

pub struct SafetyVerifier {
    rules: Vec<Box<dyn Fn(&DroneState) -> bool + Send + Sync>>,
}

impl SafetyVerifier {
    pub fn new() -> Self {
        SafetyVerifier { rules: vec![] }
    }
    pub fn verify(&self, state: &DroneState) -> bool {
        self.rules.iter().all(|rule| rule(state))
    }
}
