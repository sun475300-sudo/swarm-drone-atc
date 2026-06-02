// Phase 522: Edge ML Engine — Rust
// SDACS on-device machine learning inference for drone edge computing

use std::collections::HashMap;

// Phase 522 marker — quantized neural network inference engine

/// Fixed-point quantization parameters
#[derive(Debug, Clone)]
pub struct QuantParams {
    pub scale:      f32,
    pub zero_point: i32,
    pub bits:       u8,   // typically 8 for int8
}

impl QuantParams {
    pub fn new(scale: f32, zero_point: i32) -> Self {
        Self { scale, zero_point, bits: 8 }
    }

    /// Quantize a float to int8
    pub fn quantize(&self, x: f32) -> i8 {
        let q = (x / self.scale).round() as i32 + self.zero_point;
        q.clamp(i8::MIN as i32, i8::MAX as i32) as i8
    }

    /// Dequantize an int8 back to float
    pub fn dequantize(&self, q: i8) -> f32 {
        (q as i32 - self.zero_point) as f32 * self.scale
    }
}

/// Quantized dense layer (int8 weights)
#[derive(Debug, Clone)]
pub struct QuantizedDense {
    pub weights:    Vec<Vec<i8>>,   // [out_features][in_features]
    pub bias:       Vec<i32>,
    pub in_size:    usize,
    pub out_size:   usize,
    pub w_params:   QuantParams,
    pub act_params: QuantParams,
}

impl QuantizedDense {
    pub fn new(in_size: usize, out_size: usize) -> Self {
        // Initialize with small random-like weights (deterministic for reproducibility)
        let weights: Vec<Vec<i8>> = (0..out_size)
            .map(|i| (0..in_size)
                .map(|j| (((i * 13 + j * 7) % 50) as i8 - 25))
                .collect())
            .collect();
        Self {
            weights,
            bias: vec![0i32; out_size],
            in_size,
            out_size,
            w_params:   QuantParams::new(0.01, 0),
            act_params: QuantParams::new(0.01, 0),
        }
    }

    /// Forward pass: int8 matrix multiply + bias + ReLU
    pub fn forward(&self, input: &[i8]) -> Vec<i8> {
        assert_eq!(input.len(), self.in_size);
        (0..self.out_size).map(|i| {
            let sum: i32 = self.weights[i].iter()
                .zip(input.iter())
                .map(|(&w, &x)| w as i32 * x as i32)
                .sum::<i32>() + self.bias[i];
            // ReLU + re-quantize
            let activated = sum.max(0);
            let dequant = activated as f32 * self.w_params.scale * self.act_params.scale;
            self.act_params.quantize(dequant)
        }).collect()
    }
}

/// Edge ML model for drone anomaly detection
pub struct EdgeMLModel {
    pub layers:     Vec<QuantizedDense>,
    pub layer_names: Vec<String>,
    pub input_size:  usize,
    pub output_size: usize,
    pub version:     String,
}

impl EdgeMLModel {
    /// Create a 3-layer quantized anomaly detector
    pub fn new_anomaly_detector() -> Self {
        let layers = vec![
            QuantizedDense::new(8, 32),
            QuantizedDense::new(32, 16),
            QuantizedDense::new(16, 4),
        ];
        Self {
            layers,
            layer_names: vec![
                "encoder".into(), "hidden".into(), "classifier".into()
            ],
            input_size:  8,
            output_size: 4,
            version:     "1.0.0-int8".into(),
        }
    }

    /// Run inference — returns class probabilities (approximate, dequantized)
    pub fn infer(&self, input: &[f32]) -> Vec<f32> {
        assert_eq!(input.len(), self.input_size, "Input size mismatch");

        // Quantize input
        let q_params = QuantParams::new(0.01, 0);
        let mut hidden: Vec<i8> = input.iter()
            .map(|&x| q_params.quantize(x))
            .collect();

        // Forward through layers
        for layer in &self.layers {
            hidden = layer.forward(&hidden);
        }

        // Dequantize output
        let out_params = QuantParams::new(0.01, 0);
        hidden.iter().map(|&q| out_params.dequantize(q)).collect()
    }

    /// Batch inference
    pub fn infer_batch(&self, inputs: &[Vec<f32>]) -> Vec<Vec<f32>> {
        inputs.iter().map(|x| self.infer(x)).collect()
    }

    /// Model statistics
    pub fn stats(&self) -> HashMap<String, usize> {
        let mut s = HashMap::new();
        s.insert("num_layers".into(), self.layers.len());
        s.insert("total_params".into(), self.layers.iter()
            .map(|l| l.in_size * l.out_size + l.out_size)
            .sum());
        s
    }
}

/// Drone telemetry feature vector for anomaly detection
#[derive(Debug, Clone)]
pub struct TelemetryFeatures {
    pub speed_norm:   f32,  // 0..1
    pub altitude_norm:f32,
    pub battery_norm: f32,
    pub accel_x:      f32,
    pub accel_y:      f32,
    pub accel_z:      f32,
    pub wind_speed:   f32,
    pub rssi_norm:    f32,
}

impl TelemetryFeatures {
    pub fn to_vec(&self) -> Vec<f32> {
        vec![
            self.speed_norm, self.altitude_norm, self.battery_norm,
            self.accel_x, self.accel_y, self.accel_z,
            self.wind_speed, self.rssi_norm,
        ]
    }

    pub fn normalize(speed: f32, alt: f32, battery: f32,
                     ax: f32, ay: f32, az: f32,
                     wind: f32, rssi_dbm: f32) -> Self {
        Self {
            speed_norm:    (speed / 30.0).clamp(0.0, 1.0),
            altitude_norm: (alt   / 120.0).clamp(0.0, 1.0),
            battery_norm:  (battery / 100.0).clamp(0.0, 1.0),
            accel_x:       ax.clamp(-2.0, 2.0) / 2.0,
            accel_y:       ay.clamp(-2.0, 2.0) / 2.0,
            accel_z:       (az - 9.81).clamp(-2.0, 2.0) / 2.0,
            wind_speed:    (wind / 20.0).clamp(0.0, 1.0),
            rssi_norm:     ((rssi_dbm + 100.0) / 70.0).clamp(0.0, 1.0),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_quantize_dequantize() {
        let params = QuantParams::new(0.1, 0);
        let x = 1.5_f32;
        let q = params.quantize(x);
        let dq = params.dequantize(q);
        assert!((dq - x).abs() < 0.2, "Quantization error too large");
    }

    #[test]
    fn test_infer_output_size() {
        let model = EdgeMLModel::new_anomaly_detector();
        let features = TelemetryFeatures::normalize(
            10.0, 60.0, 80.0, 0.1, 0.0, 9.81, 5.0, -70.0
        );
        let out = model.infer(&features.to_vec());
        assert_eq!(out.len(), 4);
    }

    #[test]
    fn test_int8_layer_forward() {
        let layer = QuantizedDense::new(4, 2);
        let input = vec![10i8, -5, 20, -10];
        let out = layer.forward(&input);
        assert_eq!(out.len(), 2);
    }
}
