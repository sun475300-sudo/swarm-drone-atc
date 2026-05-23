/// Phase 280: Rust Formation Control — 고성능 군집 대형 제어
/// SIMD 최적화 가능한 벡터 연산 기반 대형 좌표 계산.

use std::collections::HashMap;

#[derive(Clone, Debug)]
pub struct Vec3 {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Vec3 {
    pub fn new(x: f64, y: f64, z: f64) -> Self { Vec3 { x, y, z } }
    pub fn zero() -> Self { Vec3 { x: 0.0, y: 0.0, z: 0.0 } }
    pub fn distance(&self, other: &Vec3) -> f64 {
        ((self.x - other.x).powi(2) + (self.y - other.y).powi(2) + (self.z - other.z).powi(2)).sqrt()
    }
    pub fn lerp(&self, other: &Vec3, t: f64) -> Vec3 {
        Vec3 {
            x: self.x * (1.0 - t) + other.x * t,
            y: self.y * (1.0 - t) + other.y * t,
            z: self.z * (1.0 - t) + other.z * t,
        }
    }
    pub fn add(&self, other: &Vec3) -> Vec3 {
        Vec3 { x: self.x + other.x, y: self.y + other.y, z: self.z + other.z }
    }
}

#[derive(Clone, Debug)]
pub enum FormationType { VFormation, Grid, Circle, Line, Diamond }

pub struct FormationEngine {
    slots: HashMap<String, Vec<Vec3>>,
}

impl FormationEngine {
    pub fn new() -> Self { FormationEngine { slots: HashMap::new() } }

    pub fn v_formation(n: usize, spacing: f64, angle_deg: f64) -> Vec<Vec3> {
        let angle = angle_deg.to_radians();
        let mut offsets = vec![Vec3::zero()];
        for i in 1..n {
            let side = if i % 2 == 1 { 1.0 } else { -1.0 };
            let rank = ((i + 1) / 2) as f64;
            offsets.push(Vec3::new(
                -rank * spacing * angle.cos(),
                side * rank * spacing * angle.sin(),
                0.0,
            ));
        }
        offsets
    }

    pub fn grid_formation(n: usize, spacing: f64) -> Vec<Vec3> {
        let cols = (n as f64).sqrt().ceil() as usize;
        (0..n).map(|i| {
            let (row, col) = (i / cols, i % cols);
            Vec3::new(row as f64 * spacing, col as f64 * spacing, 0.0)
        }).collect()
    }

    pub fn circle_formation(n: usize, radius: f64) -> Vec<Vec3> {
        (0..n).map(|i| {
            let theta = 2.0 * std::f64::consts::PI * i as f64 / n as f64;
            Vec3::new(radius * theta.cos(), radius * theta.sin(), 0.0)
        }).collect()
    }

    pub fn compute_transition(old: &[Vec3], new: &[Vec3], steps: usize) -> Vec<Vec<Vec3>> {
        (0..=steps).map(|s| {
            let t = s as f64 / steps as f64;
            let t_smooth = 3.0 * t * t - 2.0 * t * t * t;
            old.iter().zip(new.iter())
                .map(|(o, n)| o.lerp(n, t_smooth))
                .collect()
        }).collect()
    }

    pub fn compute_cohesion(positions: &[Vec3], expected: &[Vec3], leader_pos: &Vec3) -> f64 {
        if positions.is_empty() { return 0.0; }
        let errors: Vec<f64> = positions.iter().zip(expected.iter())
            .map(|(actual, offset)| actual.distance(&leader_pos.add(offset)))
            .collect();
        let avg_error = errors.iter().sum::<f64>() / errors.len() as f64;
        (1.0 - avg_error / 100.0).max(0.0)
    }

    pub fn store_formation(&mut self, id: String, offsets: Vec<Vec3>) {
        self.slots.insert(id, offsets);
    }

    pub fn get_formation(&self, id: &str) -> Option<&Vec<Vec3>> {
        self.slots.get(id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_v_formation() {
        let offsets = FormationEngine::v_formation(5, 15.0, 30.0);
        assert_eq!(offsets.len(), 5);
        assert!((offsets[0].x).abs() < 1e-6);
    }

    #[test]
    fn test_grid_formation() {
        let offsets = FormationEngine::grid_formation(9, 20.0);
        assert_eq!(offsets.len(), 9);
    }

    #[test]
    fn test_circle_formation() {
        let offsets = FormationEngine::circle_formation(8, 50.0);
        assert_eq!(offsets.len(), 8);
        for o in &offsets {
            let r = (o.x * o.x + o.y * o.y).sqrt();
            assert!((r - 50.0).abs() < 1e-6);
        }
    }

    #[test]
    fn test_transition() {
        let old = FormationEngine::grid_formation(4, 10.0);
        let new = FormationEngine::circle_formation(4, 30.0);
        let traj = FormationEngine::compute_transition(&old, &new, 10);
        assert_eq!(traj.len(), 11);
    }

    #[test]
    fn test_cohesion() {
        let leader = Vec3::new(100.0, 100.0, 50.0);
        let expected = vec![Vec3::zero(), Vec3::new(10.0, 0.0, 0.0)];
        let actual = vec![leader.clone(), Vec3::new(110.0, 100.0, 50.0)];
        let c = FormationEngine::compute_cohesion(&actual, &expected, &leader);
        assert!(c > 0.9);
    }
}
