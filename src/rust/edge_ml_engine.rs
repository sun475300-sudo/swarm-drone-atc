// Phase 522: Edge ML Engine for Drone Onboard Inference
// Quantization and int8 inference pipeline
// SDACS Edge Intelligence Module

use std::collections::HashMap;

/// int8 quantized weight tensor
#[derive(Debug, Clone)]
pub struct QuantizedTensor {
    pub data: Vec<i8>,
    pub scale: f32,
    pub zero_point: i8,
    pub shape: Vec<usize>,
}

impl QuantizedTensor {
    pub fn from_float(data: &[f32], shape: Vec<usize>) -> Self {
        let max_val = data.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let min_val = data.iter().cloned().fold(f32::INFINITY, f32::min);
        let scale = (max_val - min_val) / 255.0;
        let zero_point = (-min_val / scale) as i8;

        // quantize to int8
        let quantized: Vec<i8> = data
            .iter()
            .map(|&v| ((v / scale) + zero_point as f32).round().clamp(-128.0, 127.0) as i8)
            .collect();

        QuantizedTensor { data: quantized, scale, zero_point, shape }
    }

    /// Dequantize int8 back to float
    pub fn dequantize(&self) -> Vec<f32> {
        self.data
            .iter()
            .map(|&v| (v as f32 - self.zero_point as f32) * self.scale)
            .collect()
    }
}

/// Quantized neural network layer
#[derive(Debug)]
pub struct QuantizedLayer {
    pub weights: QuantizedTensor,
    pub bias: Vec<f32>,
    pub activation: String,
}

impl QuantizedLayer {
    /// Run inference on int8 quantized layer
    pub fn infer(&self, input: &[f32]) -> Vec<f32> {
        let weights_f32 = self.weights.dequantize();
        let out_size = self.weights.shape[0];
        let in_size = self.weights.shape[1];

        let mut output = vec![0.0f32; out_size];
        for i in 0..out_size {
            let mut sum = self.bias.get(i).copied().unwrap_or(0.0);
            for j in 0..in_size.min(input.len()) {
                sum += weights_f32[i * in_size + j] * input[j];
            }
            output[i] = match self.activation.as_str() {
                "relu" => sum.max(0.0),
                "sigmoid" => 1.0 / (1.0 + (-sum).exp()),
                _ => sum,
            };
        }
        output
    }
}

/// Edge ML inference engine with int8 quantization
pub struct EdgeMLEngine {
    pub layers: Vec<QuantizedLayer>,
    pub model_name: String,
    pub inference_count: u64,
    pub metrics: HashMap<String, f64>,
}

impl EdgeMLEngine {
    pub fn new(model_name: &str) -> Self {
        EdgeMLEngine {
            layers: Vec::new(),
            model_name: model_name.to_string(),
            inference_count: 0,
            metrics: HashMap::new(),
        }
    }

    /// Run full inference pipeline
    pub fn infer(&mut self, input: Vec<f32>) -> Vec<f32> {
        let start = std::time::Instant::now();
        let mut output = input;
        for layer in &self.layers {
            output = layer.infer(&output);
        }
        self.inference_count += 1;
        let latency = start.elapsed().as_secs_f64() * 1000.0;
        self.metrics.insert("last_latency_ms".to_string(), latency);
        output
    }

    /// quantize model weights for edge deployment
    pub fn quantize(&mut self) {
        // Post-training quantization applied to all layers
        for layer in &mut self.layers {
            let dequant = layer.weights.dequantize();
            layer.weights = QuantizedTensor::from_float(&dequant, layer.weights.shape.clone());
        }
    }
}

fn main() {
    println!("SDACS Edge ML Engine v522");
    println!("int8 quantization enabled for edge inference");
    let mut engine = EdgeMLEngine::new("collision_avoidance");
    engine.quantize();
    let input = vec![0.1, 0.2, 0.3, 0.4, 0.5];
    let result = engine.infer(input);
    println!("Inference result: {:?}", result);
    println!("Inference count: {}", engine.inference_count);
}
