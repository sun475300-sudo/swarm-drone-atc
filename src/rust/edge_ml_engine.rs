// Phase 522 — Edge ML Engine: Quantization and Inference
// Rust implementation of an on-device ML engine for drone edge inference.

use std::collections::HashMap;

/// Supported model data types for quantization
#[derive(Debug, Clone, PartialEq)]
pub enum DType {
    Float32,
    Int8,   // int8 quantized type
    Uint8,
}

/// A quantized tensor holding int8 or float32 values
#[derive(Debug, Clone)]
pub struct Tensor {
    pub data: Vec<f32>,
    pub shape: Vec<usize>,
    pub dtype: DType,
    pub scale: f32,
    pub zero_point: i32,
}

impl Tensor {
    pub fn new(data: Vec<f32>, shape: Vec<usize>) -> Self {
        Tensor {
            data,
            shape,
            dtype: DType::Float32,
            scale: 1.0,
            zero_point: 0,
        }
    }

    /// Quantize tensor to int8 (asymmetric min/max quantize)
    pub fn quantize(&self) -> QuantizedTensor {
        let min = self.data.iter().cloned().fold(f32::INFINITY, f32::min);
        let max = self.data.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let scale = (max - min) / 255.0;
        let zero_point = (-min / scale).round() as i32;
        let int8_data: Vec<i8> = self.data.iter().map(|&x| {
            let q = (x / scale + zero_point as f32).round() as i32;
            q.clamp(-128, 127) as i8
        }).collect();
        QuantizedTensor { data: int8_data, shape: self.shape.clone(), scale, zero_point }
    }

    pub fn numel(&self) -> usize {
        self.shape.iter().product()
    }
}

/// Quantized tensor in int8 format for efficient edge inference
#[derive(Debug, Clone)]
pub struct QuantizedTensor {
    pub data: Vec<i8>,
    pub shape: Vec<usize>,
    pub scale: f32,
    pub zero_point: i32,
}

impl QuantizedTensor {
    /// Dequantize back to float32
    pub fn dequantize(&self) -> Tensor {
        let float_data: Vec<f32> = self.data.iter().map(|&x| {
            (x as f32 - self.zero_point as f32) * self.scale
        }).collect();
        Tensor::new(float_data, self.shape.clone())
    }
}

/// Edge ML model layer types
#[derive(Debug, Clone)]
pub enum LayerType {
    Dense { in_features: usize, out_features: usize },
    Conv2d { in_channels: usize, out_channels: usize, kernel_size: usize },
    BatchNorm { num_features: usize },
    ReLU,
}

/// A single model layer
#[derive(Debug, Clone)]
pub struct Layer {
    pub name: String,
    pub layer_type: LayerType,
    pub weights: Option<Tensor>,
    pub bias: Option<Tensor>,
}

impl Layer {
    pub fn new(name: &str, layer_type: LayerType) -> Self {
        Layer {
            name: name.to_string(),
            layer_type,
            weights: None,
            bias: None,
        }
    }

    /// Run forward pass (stub — returns identity for demo)
    pub fn forward(&self, input: &Tensor) -> Tensor {
        // In real implementation, apply weights and activation
        input.clone()
    }
}

/// Edge inference engine with int8 quantization support
pub struct EdgeMlEngine {
    pub model_name: String,
    pub layers: Vec<Layer>,
    pub quantized: bool,
    pub quantized_weights: HashMap<String, QuantizedTensor>,
    pub inference_count: u64,
}

impl EdgeMlEngine {
    pub fn new(model_name: &str) -> Self {
        EdgeMlEngine {
            model_name: model_name.to_string(),
            layers: Vec::new(),
            quantized: false,
            quantized_weights: HashMap::new(),
            inference_count: 0,
        }
    }

    /// Add a layer to the model
    pub fn add_layer(&mut self, layer: Layer) {
        self.layers.push(layer);
    }

    /// Quantize all layer weights to int8 for edge deployment
    pub fn quantize_model(&mut self) {
        for layer in &self.layers {
            if let Some(ref weights) = layer.weights {
                let qt = weights.quantize();
                self.quantized_weights.insert(layer.name.clone(), qt);
            }
        }
        self.quantized = true;
        println!("[EdgeMlEngine] Model quantized to int8 — {} layers", self.layers.len());
    }

    /// Run inference on input tensor
    pub fn infer(&mut self, input: Tensor) -> Result<Tensor, String> {
        if self.layers.is_empty() {
            return Err("No layers defined in model".to_string());
        }
        let mut output = input;
        for layer in &self.layers {
            output = layer.forward(&output);
        }
        self.inference_count += 1;
        Ok(output)
    }

    /// Benchmark inference latency (stub)
    pub fn benchmark(&mut self, input: Tensor, iterations: u32) -> f64 {
        let start = std::time::Instant::now();
        for _ in 0..iterations {
            let _ = self.infer(input.clone());
        }
        start.elapsed().as_secs_f64() / iterations as f64
    }

    pub fn model_info(&self) -> String {
        format!(
            "Model: {} | Layers: {} | Quantized: {} | Inferences: {}",
            self.model_name, self.layers.len(), self.quantized, self.inference_count
        )
    }
}

/// Build a default tiny edge model for drone object detection
pub fn build_default_edge_model() -> EdgeMlEngine {
    let mut engine = EdgeMlEngine::new("drone_detect_tiny");
    engine.add_layer(Layer::new("conv1", LayerType::Conv2d { in_channels: 3, out_channels: 16, kernel_size: 3 }));
    engine.add_layer(Layer::new("relu1", LayerType::ReLU));
    engine.add_layer(Layer::new("bn1", LayerType::BatchNorm { num_features: 16 }));
    engine.add_layer(Layer::new("fc1", LayerType::Dense { in_features: 256, out_features: 10 }));
    engine
}

fn main() {
    println!("Edge ML Engine — Phase 522");
    let mut engine = build_default_edge_model();
    engine.quantize_model();
    let input = Tensor::new(vec![0.5_f32; 256], vec![1, 256]);
    match engine.infer(input) {
        Ok(out) => println!("Inference OK, output numel={}", out.numel()),
        Err(e) => eprintln!("Inference error: {}", e),
    }
    println!("{}", engine.model_info());
}
