//! SDACS Edge ML Engine — Rust (Phase 522)
//! 드론 엣지 디바이스용 경량 ML 추론 엔진 (int8 양자화)

use std::collections::HashMap;

/// int8 양자화된 가중치
#[derive(Debug, Clone)]
pub struct QuantizedLayer {
    pub weights: Vec<i8>,
    pub scale: f32,
    pub zero_point: i8,
    pub input_size: usize,
    pub output_size: usize,
}

impl QuantizedLayer {
    pub fn new(input_size: usize, output_size: usize, scale: f32) -> Self {
        let weights = vec![0i8; input_size * output_size];
        Self { weights, scale, zero_point: 0, input_size, output_size }
    }

    /// float32 -> int8 양자화
    pub fn quantize(values: &[f32], scale: f32, zero_point: i8) -> Vec<i8> {
        values.iter().map(|&v| {
            let quantized = (v / scale).round() as i32 + zero_point as i32;
            quantized.clamp(-128, 127) as i8
        }).collect()
    }

    /// int8 -> float32 역양자화
    pub fn dequantize(quantized: &[i8], scale: f32, zero_point: i8) -> Vec<f32> {
        quantized.iter().map(|&q| {
            (q as i32 - zero_point as i32) as f32 * scale
        }).collect()
    }

    /// 행렬 곱셈 (int8 추론)
    pub fn infer(&self, input: &[f32]) -> Vec<f32> {
        assert_eq!(input.len(), self.input_size);
        let quantized_input = Self::quantize(input, self.scale, self.zero_point);
        let mut output = vec![0i32; self.output_size];

        for (j, out) in output.iter_mut().enumerate() {
            for (i, &inp) in quantized_input.iter().enumerate() {
                *out += inp as i32 * self.weights[j * self.input_size + i] as i32;
            }
        }

        output.iter().map(|&v| v as f32 * self.scale * self.scale).collect()
    }
}

/// 경량 MLP 추론 엔진
#[derive(Debug)]
pub struct EdgeMLEngine {
    pub layers: Vec<QuantizedLayer>,
    pub model_name: String,
    inference_count: u64,
}

impl EdgeMLEngine {
    pub fn new(name: &str) -> Self {
        Self {
            layers: Vec::new(),
            model_name: name.to_string(),
            inference_count: 0,
        }
    }

    pub fn add_layer(&mut self, layer: QuantizedLayer) {
        self.layers.push(layer);
    }

    /// 순전파 추론 (Phase 522 — int8 양자화 전체 경로)
    pub fn infer(&mut self, input: &[f32]) -> Vec<f32> {
        self.inference_count += 1;
        let mut current = input.to_vec();
        for layer in &self.layers {
            current = layer.infer(&current);
            // ReLU 활성화
            current.iter_mut().for_each(|v| *v = v.max(0.0));
        }
        current
    }

    pub fn inference_count(&self) -> u64 {
        self.inference_count
    }

    /// 충돌 위험도 예측 (드론 간 거리 → 위험도)
    pub fn predict_collision_risk(&mut self, distance: f32, relative_speed: f32) -> f32 {
        let input = vec![distance / 100.0, relative_speed / 20.0];
        let output = self.infer(&input);
        output.first().copied().unwrap_or(0.0).clamp(0.0, 1.0)
    }
}

/// 배터리 수명 예측 모델
pub struct BatteryLifePredictor {
    engine: EdgeMLEngine,
}

impl BatteryLifePredictor {
    pub fn new() -> Self {
        let mut engine = EdgeMLEngine::new("battery_life_v1");
        let layer = QuantizedLayer::new(3, 1, 0.01);
        engine.add_layer(layer);
        Self { engine }
    }

    /// 남은 비행 시간 예측 (분)
    pub fn predict_remaining_minutes(&mut self, battery_pct: f32, speed: f32, altitude: f32) -> f32 {
        let input = vec![battery_pct / 100.0, speed / 15.0, altitude / 400.0];
        let output = self.engine.infer(&input);
        output.first().copied().unwrap_or(0.0) * 60.0
    }
}

/// 모델 레지스트리
pub struct ModelRegistry {
    models: HashMap<String, EdgeMLEngine>,
}

impl ModelRegistry {
    pub fn new() -> Self {
        Self { models: HashMap::new() }
    }

    pub fn register(&mut self, name: &str, engine: EdgeMLEngine) {
        self.models.insert(name.to_string(), engine);
    }

    pub fn get_mut(&mut self, name: &str) -> Option<&mut EdgeMLEngine> {
        self.models.get_mut(name)
    }

    pub fn model_count(&self) -> usize {
        self.models.len()
    }
}
