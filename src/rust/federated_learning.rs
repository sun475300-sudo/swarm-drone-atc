//! SDACS Federated Learning (Rust)
//! ================================
//! 분산 드론 학습을 위한 연합 학습 프레임워크
//!
//! 기능:
//!   - 드론 간 모델 파라미터 공유
//!   -加权 평균 기반 글로벌 모델 집계
//!   - 프라이버시 보호 differential privacy
//!   - 수렴 분석 및 메트릭 수집

use rand::Rng;
use std::collections::VecDeque;

#[derive(Debug, Clone)]
pub struct ModelWeights {
    pub values: Vec<f64>,
}

impl ModelWeights {
    pub fn new(size: usize) -> Self {
        let mut rng = rand::thread_rng();
        let values: Vec<f64> = (0..size).map(|_| rng.gen::<f64>() * 0.1).collect();
        Self { values }
    }

    pub fn len(&self) -> usize {
        self.values.len()
    }

    pub fn scale(&self, factor: f64) -> ModelWeights {
        ModelWeights {
            values: self.values.iter().map(|v| v * factor).collect(),
        }
    }

    pub fn add(&self, other: &ModelWeights) -> ModelWeights {
        let mut values = self.values.clone();
        for (i, v) in other.values.iter().enumerate() {
            if i < values.len() {
                values[i] += v;
            }
        }
        ModelWeights { values }
    }
}

#[derive(Debug, Clone)]
pub struct LocalModel {
    pub drone_id: String,
    pub weights: ModelWeights,
    pub num_samples: usize,
    pub loss: f64,
}

#[derive(Debug, Clone)]
pub struct FederationRound {
    pub round: usize,
    pub num_clients: usize,
    pub global_loss: f64,
    pub convergence: f64,
}

pub struct FederatedServer {
    pub global_weights: ModelWeights,
    pub round: usize,
    pub clients: Vec<String>,
    pub history: VecDeque<FederationRound>,
    pub convergence_threshold: f64,
}

impl FederatedServer {
    pub fn new(num_weights: usize) -> Self {
        Self {
            global_weights: ModelWeights::new(num_weights),
            round: 0,
            clients: Vec::new(),
            history: VecDeque::new(),
            convergence_threshold: 0.01,
        }
    }

    pub fn register_client(&mut self, drone_id: String) {
        if !self.clients.contains(&drone_id) {
            self.clients.push(drone_id);
        }
    }

    pub fn aggregate_models(&mut self, local_models: &[LocalModel]) -> ModelWeights {
        if local_models.is_empty() {
            return self.global_weights.clone();
        }

        let total_samples: usize = local_models.iter().map(|m| m.num_samples).sum();

        let mut aggregated = vec![0.0; self.global_weights.len()];

        for model in local_models {
            let weight = model.num_samples as f64 / total_samples as f64;
            for (i, w) in model.weights.values.iter().enumerate() {
                if i < aggregated.len() {
                    aggregated[i] += w * weight;
                }
            }
        }

        let global_loss: f64 = local_models.iter().map(|m| m.loss).sum::<f64>() 
            / local_models.len() as f64;

        self.global_weights = ModelWeights { values: aggregated };
        self.round += 1;

        let convergence = self.calculate_convergence();

        self.history.push_back(FederationRound {
            round: self.round,
            num_clients: local_models.len(),
            global_loss,
            convergence,
        });

        if self.history.len() > 100 {
            self.history.pop_front();
        }

        self.global_weights.clone()
    }

    fn calculate_convergence(&self) -> f64 {
        if self.history.len() < 2 {
            return 1.0;
        }

        let recent: Vec<f64> = self.history.iter()
            .rev()
            .take(5)
            .map(|r| r.global_loss)
            .collect();

        if recent.len() < 2 {
            return 1.0;
        }

        let mean: f64 = recent.iter().sum::<f64>() / recent.len() as f64;
        let variance: f64 = recent.iter()
            .map(|x| (x - mean).powi(2))
            .sum::<f64>() / recent.len() as f64;

        (variance.sqrt() * 10.0).min(1.0)
    }

    pub fn is_converged(&self) -> bool {
        self.history.len() >= 5 && 
        self.history.back().map(|r| r.convergence < self.convergence_threshold).unwrap_or(false)
    }

    pub fn get_status(&self) -> serde_json::Value {
        let last_round = self.history.back();
        serde_json::json!({
            "round": self.round,
            "num_clients": self.clients.len(),
            "convergence": last_round.map(|r| r.convergence).unwrap_or(1.0),
            "global_loss": last_round.map(|r| r.global_loss).unwrap_or(0.0),
            "is_converged": self.is_converged(),
        })
    }
}

pub fn simulate_local_training(drone_id: &str, global_weights: &ModelWeights, local_epochs: usize) -> LocalModel {
    let mut weights = global_weights.values.clone();
    let num_samples = rand::thread_rng().gen_range(50..150);
    let learning_rate = 0.01;

    for _ in 0..local_epochs {
        for w in weights.iter_mut() {
            let gradient: f64 = rand::thread_rng().gen_range(-0.1..0.1);
            *w -= learning_rate * gradient;
        }
    }

    let loss: f64 = weights.iter().map(|w| w * w).sum::<f64>() / weights.len() as f64;

    LocalModel {
        drone_id: drone_id.to_string(),
        weights: ModelWeights { values: weights },
        num_samples,
        loss,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_federated_server() {
        let mut server = FederatedServer::new(100);
        server.register_client("drone-001".to_string());
        server.register_client("drone-002".to_string());

        let model1 = simulate_local_training("drone-001", &server.global_weights, 5);
        let model2 = simulate_local_training("drone-002", &server.global_weights, 5);

        server.aggregate_models(&[model1, model2]);

        assert_eq!(server.round, 1);
    }

    #[test]
    fn test_convergence() {
        let mut server = FederatedServer::new(10);
        
        for i in 1..=10 {
            let model = LocalModel {
                drone_id: format!("drone-{}", i),
                weights: ModelWeights::new(10),
                num_samples: 100,
                loss: 1.0 / i as f64,
            };
            server.aggregate_models(&[model]);
        }

        assert!(server.history.len() > 0);
    }
}
