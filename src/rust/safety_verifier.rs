// Phase 652 — Safety Verifier (Rust)
// 드론 충돌 안전성 형식 검증기

use std::collections::HashMap;

/// 드론 위치 (미터 단위 3D 벡터).
#[derive(Debug, Clone)]
pub struct Position {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Position {
    pub fn distance_to(&self, other: &Position) -> f64 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        let dz = self.z - other.z;
        (dx * dx + dy * dy + dz * dz).sqrt()
    }
}

/// 안전 검증 결과.
#[derive(Debug)]
pub struct VerificationResult {
    pub safe: bool,
    pub violations: Vec<String>,
}

/// 군집 드론 안전 속성 검증기.
pub struct SafetyVerifier {
    pub safe_separation_m: f64,
    pub min_altitude_m: f64,
    pub max_altitude_m: f64,
    pub max_speed_ms: f64,
}

impl Default for SafetyVerifier {
    fn default() -> Self {
        SafetyVerifier {
            safe_separation_m: 30.0,
            min_altitude_m: 20.0,
            max_altitude_m: 400.0,
            max_speed_ms: 20.0,
        }
    }
}

impl SafetyVerifier {
    /// 드론 위치들의 안전 속성을 검증한다.
    pub fn verify(&self, positions: &HashMap<String, Position>) -> VerificationResult {
        let mut violations = Vec::new();

        // 고도 한계 검사
        for (id, pos) in positions {
            if pos.z < self.min_altitude_m {
                violations.push(format!("{}: altitude {:.1}m below minimum {:.1}m", id, pos.z, self.min_altitude_m));
            }
            if pos.z > self.max_altitude_m {
                violations.push(format!("{}: altitude {:.1}m exceeds maximum {:.1}m", id, pos.z, self.max_altitude_m));
            }
        }

        // 분리 거리 검사
        let ids: Vec<&String> = positions.keys().collect();
        for i in 0..ids.len() {
            for j in (i + 1)..ids.len() {
                let a = ids[i];
                let b = ids[j];
                let dist = positions[a].distance_to(&positions[b]);
                if dist < self.safe_separation_m {
                    violations.push(format!(
                        "{} <-> {}: separation {:.1}m < {:.1}m",
                        a, b, dist, self.safe_separation_m
                    ));
                }
            }
        }

        VerificationResult {
            safe: violations.is_empty(),
            violations,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_safe_positions() {
        let verifier = SafetyVerifier::default();
        let mut positions = HashMap::new();
        positions.insert("D-001".into(), Position { x: 0.0, y: 0.0, z: 100.0 });
        positions.insert("D-002".into(), Position { x: 100.0, y: 0.0, z: 100.0 });
        let result = verifier.verify(&positions);
        assert!(result.safe);
    }
}
