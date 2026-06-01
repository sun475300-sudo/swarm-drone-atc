// Phase 522: Edge ML Engine for SDACS
// 드론 온보드 경량 머신러닝 추론 엔진
// Int8 양자화 및 실시간 추론 지원

use std::collections::HashMap;

/// Int8 양자화된 텐서
#[derive(Debug, Clone)]
pub struct QuantizedTensor {
    pub data: Vec<i8>,
    pub scale: f32,
    pub zero_point: i8,
    pub shape: Vec<usize>,
}

impl QuantizedTensor {
    pub fn new(shape: Vec<usize>) -> Self {
        let size = shape.iter().product();
        Self {
            data: vec![0i8; size],
            scale: 1.0,
            zero_point: 0,
            shape,
        }
    }

    /// Float32 텐서를 Int8로 양자화 (quantize)
    pub fn from_f32(data: &[f32], bits: u8) -> Self {
        assert_eq!(bits, 8, "Only int8 quantization supported");
        let max_val = data.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let min_val = data.iter().cloned().fold(f32::INFINITY, f32::min);
        let scale = (max_val - min_val) / 255.0;
        let zero_point = (-min_val / scale - 128.0) as i8;
        let quantized: Vec<i8> = data
            .iter()
            .map(|&x| {
                let q = (x / scale + zero_point as f32).round() as i32;
                q.clamp(-128, 127) as i8
            })
            .collect();
        Self {
            data: quantized,
            scale,
            zero_point,
            shape: vec![data.len()],
        }
    }

    /// Int8 -> Float32 역양자화 (dequantize)
    pub fn to_f32(&self) -> Vec<f32> {
        self.data
            .iter()
            .map(|&x| (x as f32 - self.zero_point as f32) * self.scale)
            .collect()
    }
}

/// 경량 신경망 레이어
#[derive(Debug, Clone)]
pub struct LinearLayer {
    pub weights: QuantizedTensor,
    pub bias: Vec<f32>,
    pub in_features: usize,
    pub out_features: usize,
}

impl LinearLayer {
    pub fn new(in_features: usize, out_features: usize) -> Self {
        Self {
            weights: QuantizedTensor::new(vec![out_features, in_features]),
            bias: vec![0.0; out_features],
            in_features,
            out_features,
        }
    }

    /// 추론 (infer) - Int8 행렬 곱
    pub fn infer(&self, input: &[f32]) -> Vec<f32> {
        assert_eq!(input.len(), self.in_features);
        let mut output = self.bias.clone();
        let w_f32 = self.weights.to_f32();
        for (o, out) in output.iter_mut().enumerate() {
            for (i, inp) in input.iter().enumerate() {
                *out += w_f32[o * self.in_features + i] * inp;
            }
        }
        output
    }

    /// ReLU 활성화 함수
    pub fn relu(x: &[f32]) -> Vec<f32> {
        x.iter().map(|&v| v.max(0.0)).collect()
    }
}

/// Edge ML 모델 - 드론 장애물 분류기
#[derive(Debug)]
pub struct EdgeObstacleClassifier {
    pub layers: Vec<LinearLayer>,
    pub quantized: bool,
    pub model_name: String,
}

impl EdgeObstacleClassifier {
    pub fn new(input_dim: usize) -> Self {
        let l1 = LinearLayer::new(input_dim, 32);
        let l2 = LinearLayer::new(32, 16);
        let l3 = LinearLayer::new(16, 4);
        Self {
            layers: vec![l1, l2, l3],
            quantized: true,
            model_name: "EdgeObstacle_int8".to_string(),
        }
    }

    /// 모델 추론 실행
    pub fn infer(&self, input: &[f32]) -> Vec<f32> {
        let mut x = input.to_vec();
        for (i, layer) in self.layers.iter().enumerate() {
            x = layer.infer(&x);
            if i < self.layers.len() - 1 {
                x = LinearLayer::relu(&x);
            }
        }
        x
    }

    /// Softmax 출력
    pub fn softmax(logits: &[f32]) -> Vec<f32> {
        let max = logits.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let exps: Vec<f32> = logits.iter().map(|&x| (x - max).exp()).collect();
        let sum: f32 = exps.iter().sum();
        exps.iter().map(|&e| e / sum).collect()
    }

    /// 모델 크기 (bytes)
    pub fn model_size_bytes(&self) -> usize {
        self.layers.iter().map(|l| l.weights.data.len()).sum()
    }
}

/// Edge ML 추론 파이프라인 (Phase 522)
pub struct EdgeMLPipeline {
    pub classifier: EdgeObstacleClassifier,
    pub inference_count: u64,
    pub latency_us: Vec<u64>,
    pub metadata: HashMap<String, String>,
}

impl EdgeMLPipeline {
    pub fn new(input_dim: usize) -> Self {
        let mut meta = HashMap::new();
        meta.insert("phase".to_string(), "522".to_string());
        meta.insert("quantization".to_string(), "int8".to_string());
        meta.insert("target".to_string(), "drone_edge".to_string());
        Self {
            classifier: EdgeObstacleClassifier::new(input_dim),
            inference_count: 0,
            latency_us: Vec::new(),
            metadata: meta,
        }
    }

    pub fn run_infer(&mut self, sensor_data: &[f32]) -> Vec<f32> {
        self.inference_count += 1;
        let logits = self.classifier.infer(sensor_data);
        EdgeObstacleClassifier::softmax(&logits)
    }

    pub fn avg_latency_us(&self) -> f64 {
        if self.latency_us.is_empty() {
            return 0.0;
        }
        self.latency_us.iter().sum::<u64>() as f64 / self.latency_us.len() as f64
    }

    pub fn model_info(&self) -> String {
        format!(
            "EdgeML Phase 522 | int8 quantized | size={}B | inferences={}",
            self.classifier.model_size_bytes(),
            self.inference_count
        )
    }
}

fn main() {
    println!("SDACS Phase 522: Edge ML Engine");
    let mut pipeline = EdgeMLPipeline::new(12);
    let input = vec![0.5f32; 12];
    let probs = pipeline.run_infer(&input);
    println!("Inference output: {:?}", &probs[..4]);
    println!("{}", pipeline.model_info());

    // quantize test
    let floats = vec![0.1f32, 0.5, -0.3, 0.8, -1.0, 1.0];
    let qt = QuantizedTensor::from_f32(&floats, 8);
    let restored = qt.to_f32();
    println!("Quantization error: {:.6}",
        floats.iter().zip(restored.iter()).map(|(a, b)| (a - b).abs()).sum::<f32>() / floats.len() as f32
    );
}
