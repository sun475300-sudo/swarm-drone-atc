// P522: EdgeMLEngine - Rust on-device machine learning for drone inference
// Phase 522: int8 quantized inference engine for edge computing

use std::collections::HashMap;

/// int8 quantization parameters
#[derive(Debug, Clone)]
pub struct QuantizationParams {
    pub scale: f32,
    pub zero_point: i32,
    pub min_val: f32,
    pub max_val: f32,
}

impl QuantizationParams {
    pub fn from_range(min_val: f32, max_val: f32) -> Self {
        let scale = (max_val - min_val) / 255.0;
        let zero_point = -(min_val / scale).round() as i32;
        QuantizationParams { scale, zero_point, min_val, max_val }
    }

    pub fn quantize(&self, x: f32) -> i8 {
        let q = (x / self.scale + self.zero_point as f32).round() as i32;
        q.clamp(-128, 127) as i8
    }

    pub fn dequantize(&self, q: i8) -> f32 {
        (q as i32 - self.zero_point) as f32 * self.scale
    }
}

/// Quantized tensor
#[derive(Debug, Clone)]
pub struct QuantizedTensor {
    pub data: Vec<i8>,
    pub shape: Vec<usize>,
    pub params: QuantizationParams,
}

impl QuantizedTensor {
    pub fn from_float(data: &[f32], shape: Vec<usize>) -> Self {
        let min_val = data.iter().cloned().fold(f32::INFINITY, f32::min);
        let max_val = data.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let params = QuantizationParams::from_range(min_val, max_val);
        let quantized: Vec<i8> = data.iter().map(|&x| params.quantize(x)).collect();
        QuantizedTensor { data: quantized, shape, params }
    }

    pub fn to_float(&self) -> Vec<f32> {
        self.data.iter().map(|&q| self.params.dequantize(q)).collect()
    }
}

/// Edge ML inference engine
pub struct EdgeMLEngine {
    pub name: String,
    layers: Vec<Box<dyn Layer>>,
    pub infer_count: u64,
}

trait Layer: Send + Sync {
    fn forward(&self, input: &[f32]) -> Vec<f32>;
    fn name(&self) -> &str;
}

struct LinearLayer {
    weights: Vec<Vec<f32>>,
    bias: Vec<f32>,
    layer_name: String,
}

impl Layer for LinearLayer {
    fn forward(&self, input: &[f32]) -> Vec<f32> {
        self.weights.iter().zip(self.bias.iter())
            .map(|(row, b)| row.iter().zip(input).map(|(w, x)| w * x).sum::<f32>() + b)
            .collect()
    }
    fn name(&self) -> &str { &self.layer_name }
}

impl EdgeMLEngine {
    pub fn new(name: &str) -> Self {
        EdgeMLEngine { name: name.to_string(), layers: Vec::new(), infer_count: 0 }
    }

    pub fn add_linear_layer(&mut self, in_dim: usize, out_dim: usize) {
        let weights = vec![vec![0.01f32; in_dim]; out_dim];
        let bias = vec![0.0f32; out_dim];
        self.layers.push(Box::new(LinearLayer {
            weights,
            bias,
            layer_name: format!("linear_{}", self.layers.len()),
        }));
    }

    pub fn infer(&mut self, input: &[f32]) -> Vec<f32> {
        self.infer_count += 1;
        let mut out = input.to_vec();
        for layer in &self.layers {
            out = layer.forward(&out);
        }
        out
    }

    pub fn infer_quantized(&mut self, input: &[f32]) -> Vec<f32> {
        let qt = QuantizedTensor::from_float(input, vec![input.len()]);
        let dequant = qt.to_float();
        self.infer(&dequant)
    }
}
