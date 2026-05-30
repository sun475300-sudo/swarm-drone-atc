// Phase 522: edge_ml_engine — Rust 기반 엣지 ML 추론 엔진
// SDACS Edge Machine Learning Engine for On-Device Inference

use std::fmt;

/// INT8 양자화된 가중치 표현
#[derive(Debug, Clone)]
pub struct QuantizedWeight {
    pub data: Vec<i8>,
    pub scale: f32,
    pub zero_point: i8,
}

impl QuantizedWeight {
    pub fn new(data: Vec<i8>, scale: f32, zero_point: i8) -> Self {
        Self { data, scale, zero_point }
    }

    /// INT8 → FP32 역양자화 (dequantize)
    pub fn dequantize(&self) -> Vec<f32> {
        self.data
            .iter()
            .map(|&x| (x as f32 - self.zero_point as f32) * self.scale)
            .collect()
    }
}

/// FP32 → INT8 양자화 함수
pub fn quantize(values: &[f32], scale: f32, zero_point: i8) -> QuantizedWeight {
    let data: Vec<i8> = values
        .iter()
        .map(|&v| {
            let q = (v / scale + zero_point as f32).round() as i32;
            q.clamp(i8::MIN as i32, i8::MAX as i32) as i8
        })
        .collect();
    QuantizedWeight::new(data, scale, zero_point)
}

/// 경량 완전 연결 레이어 (INT8 추론)
#[derive(Debug)]
pub struct QuantizedLinear {
    pub weight: QuantizedWeight,
    pub bias: Vec<f32>,
    pub in_features: usize,
    pub out_features: usize,
}

impl QuantizedLinear {
    pub fn new(in_features: usize, out_features: usize, scale: f32) -> Self {
        // 단순화된 초기화 — 실제는 학습된 가중치 로드
        let w_data: Vec<i8> = (0..(in_features * out_features))
            .map(|i| ((i as i32 * 7 + 3) % 256 - 128) as i8)
            .collect();
        let bias = vec![0.01f32; out_features];
        Self {
            weight: QuantizedWeight::new(w_data, scale, 0),
            bias,
            in_features,
            out_features,
        }
    }

    /// INT8 행렬-벡터 곱 추론 (infer)
    pub fn infer(&self, input: &[f32]) -> Vec<f32> {
        assert_eq!(input.len(), self.in_features, "입력 크기 불일치");
        let weights_fp = self.weight.dequantize();
        let mut output = vec![0.0f32; self.out_features];
        for o in 0..self.out_features {
            let mut sum = self.bias[o];
            for i in 0..self.in_features {
                sum += weights_fp[o * self.in_features + i] * input[i];
            }
            output[o] = sum.max(0.0); // ReLU 활성화
        }
        output
    }
}

/// 엣지 추론 파이프라인
#[derive(Debug)]
pub struct EdgeInferencePipeline {
    pub layers: Vec<QuantizedLinear>,
    pub model_name: String,
}

impl EdgeInferencePipeline {
    pub fn new(model_name: &str, layer_sizes: &[(usize, usize)]) -> Self {
        let layers = layer_sizes
            .iter()
            .map(|&(in_f, out_f)| QuantizedLinear::new(in_f, out_f, 0.01))
            .collect();
        Self { layers, model_name: model_name.to_string() }
    }

    /// 전체 파이프라인 순방향 추론 (infer)
    pub fn infer(&self, input: &[f32]) -> Vec<f32> {
        let mut x = input.to_vec();
        for layer in &self.layers {
            x = layer.infer(&x);
        }
        x
    }

    pub fn memory_kb(&self) -> f32 {
        let total_params: usize = self.layers
            .iter()
            .map(|l| l.in_features * l.out_features + l.out_features)
            .sum();
        // INT8 가중치 + FP32 편향
        (total_params as f32 * 1.0 + total_params as f32 * 4.0) / 1024.0
    }
}

impl fmt::Display for EdgeInferencePipeline {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "EdgeML[{}] layers={} mem={:.1}KB",
            self.model_name, self.layers.len(), self.memory_kb())
    }
}

fn main() {
    println!("SDACS Edge ML Engine — Phase 522\n");

    // 드론 배터리 수명 예측 모델 (INT8 양자화)
    let pipeline = EdgeInferencePipeline::new(
        "battery_predictor_int8",
        &[(8, 16), (16, 8), (8, 1)],
    );
    println!("{}", pipeline);

    // 추론 실행
    let telemetry = vec![85.0, 50.0, 5.0, 20.0, 1.0, 0.5, 25.0, 2.5];
    let result = pipeline.infer(&telemetry);
    println!("배터리 잔여 시간 예측: {:.1}분", result[0].abs() * 100.0);

    // 양자화 테스트
    let fp32_weights = vec![0.1, -0.2, 0.3, -0.4, 0.5];
    let quantized = quantize(&fp32_weights, 0.01, 0);
    let dequantized = quantized.dequantize();
    println!("\n양자화 오차 (INT8):");
    for (orig, deq) in fp32_weights.iter().zip(dequantized.iter()) {
        println!("  원본={:.3} → 역양자화={:.3} (오차={:.4})", orig, deq, (orig - deq).abs());
    }
    println!("\n엣지 ML 추론 완료.");
}
