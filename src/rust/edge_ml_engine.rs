//! Phase 522 — Edge ML inference engine in Rust.
//! INT8 quantization pipeline and inference for drone path prediction model.
//! Designed for resource-constrained edge nodes aboard each drone unit.

use std::collections::VecDeque;

// --- Phase marker ---
pub const PHASE_MARKER: u32 = 522;

// --- Quantization parameters ---
pub const INT8_MIN: i8 = i8::MIN;
pub const INT8_MAX: i8 = i8::MAX;
pub const SCALE_DEFAULT: f32 = 0.01;
pub const ZERO_POINT_DEFAULT: i32 = 0;

// --- Tensor shapes for path prediction model ---
pub const INPUT_DIM: usize = 12;  // [pos_x, pos_y, pos_z, vel_x, vel_y, vel_z, heading, battery, wind_x, wind_y, wind_z, time_delta]
pub const HIDDEN_DIM: usize = 32;
pub const OUTPUT_DIM: usize = 6;  // [next_pos_x, next_pos_y, next_pos_z, next_vel_x, next_vel_y, next_vel_z]

/// Quantized weight matrix stored as INT8 values.
#[derive(Debug, Clone)]
pub struct QuantizedLayer {
    pub weights: Vec<i8>,
    pub biases: Vec<i32>,
    pub rows: usize,
    pub cols: usize,
    pub scale: f32,
    pub zero_point: i32,
}

impl QuantizedLayer {
    /// Quantize a float weight matrix into INT8 representation.
    /// Uses symmetric quantization: scale = max_abs / 127.
    pub fn quantize(float_weights: &[f32], float_biases: &[f32], rows: usize, cols: usize) -> Self {
        let max_abs = float_weights
            .iter()
            .map(|w| w.abs())
            .fold(0.0_f32, f32::max);
        let scale = if max_abs == 0.0 { SCALE_DEFAULT } else { max_abs / 127.0 };
        let zero_point = ZERO_POINT_DEFAULT;

        let weights: Vec<i8> = float_weights
            .iter()
            .map(|&w| {
                let q = (w / scale).round() as i32;
                q.clamp(INT8_MIN as i32, INT8_MAX as i32) as i8
            })
            .collect();

        let biases: Vec<i32> = float_biases
            .iter()
            .map(|&b| (b / (scale * scale)).round() as i32)
            .collect();

        QuantizedLayer { weights, biases, rows, cols, scale, zero_point }
    }

    /// Dequantize i8 weight back to f32 for verification.
    pub fn dequantize_weight(&self, idx: usize) -> f32 {
        (self.weights[idx] as f32 - self.zero_point as f32) * self.scale
    }

    /// INT8 matrix-vector multiply with bias accumulation.
    /// Accumulates in i32 to avoid overflow, then converts to f32 output.
    pub fn infer(&self, input: &[i8]) -> Vec<f32> {
        assert_eq!(input.len(), self.cols, "infer: input dimension mismatch");
        let mut output = vec![0.0_f32; self.rows];
        for r in 0..self.rows {
            let mut acc: i32 = self.biases[r];
            for c in 0..self.cols {
                acc += self.weights[r * self.cols + c] as i32 * input[c] as i32;
            }
            output[r] = acc as f32 * self.scale * self.scale;
        }
        output
    }
}

/// Full path-prediction model: input → hidden → output (two INT8 quantized layers).
#[derive(Debug)]
pub struct PathPredictionModel {
    pub layer1: QuantizedLayer,
    pub layer2: QuantizedLayer,
    pub phase: u32,
}

impl PathPredictionModel {
    /// Build a zeroed stub model (weights loaded from file in production).
    pub fn new_stub() -> Self {
        let w1 = vec![0.01_f32; HIDDEN_DIM * INPUT_DIM];
        let b1 = vec![0.0_f32; HIDDEN_DIM];
        let w2 = vec![0.01_f32; OUTPUT_DIM * HIDDEN_DIM];
        let b2 = vec![0.0_f32; OUTPUT_DIM];
        PathPredictionModel {
            layer1: QuantizedLayer::quantize(&w1, &b1, HIDDEN_DIM, INPUT_DIM),
            layer2: QuantizedLayer::quantize(&w2, &b2, OUTPUT_DIM, HIDDEN_DIM),
            phase: PHASE_MARKER,
        }
    }

    /// Quantize a float input vector to i8 using per-layer scale.
    fn quantize_input(input: &[f32], scale: f32) -> Vec<i8> {
        input
            .iter()
            .map(|&v| {
                let q = (v / scale).round() as i32;
                q.clamp(INT8_MIN as i32, INT8_MAX as i32) as i8
            })
            .collect()
    }

    /// ReLU activation for f32 slice (applied between layers).
    fn relu(v: &mut [f32]) {
        for x in v.iter_mut() {
            if *x < 0.0 { *x = 0.0; }
        }
    }

    /// Run full inference: quantize input → layer1 → ReLU → layer2 → output.
    pub fn infer(&self, input: &[f32]) -> Vec<f32> {
        assert_eq!(input.len(), INPUT_DIM, "PathPredictionModel::infer: wrong input size");
        let q_input = Self::quantize_input(input, self.layer1.scale);
        let mut hidden = self.layer1.infer(&q_input);
        Self::relu(&mut hidden);
        let q_hidden = Self::quantize_input(&hidden, self.layer2.scale);
        self.layer2.infer(&q_hidden)
    }
}

/// Rolling inference buffer for time-series smoothing (FIFO window).
pub struct InferenceBuffer {
    window: VecDeque<Vec<f32>>,
    capacity: usize,
}

impl InferenceBuffer {
    pub fn new(capacity: usize) -> Self {
        InferenceBuffer { window: VecDeque::with_capacity(capacity), capacity }
    }

    pub fn push(&mut self, prediction: Vec<f32>) {
        if self.window.len() == self.capacity {
            self.window.pop_front();
        }
        self.window.push_back(prediction);
    }

    /// Return element-wise mean of buffered predictions.
    pub fn smoothed_output(&self) -> Option<Vec<f32>> {
        if self.window.is_empty() { return None; }
        let dim = self.window[0].len();
        let mut avg = vec![0.0_f32; dim];
        for pred in &self.window {
            for (i, &v) in pred.iter().enumerate() {
                avg[i] += v;
            }
        }
        let n = self.window.len() as f32;
        for v in avg.iter_mut() { *v /= n; }
        Some(avg)
    }
}

// --- Public API for edge node integration ---

/// Run one inference step on sensor telemetry, returning smoothed trajectory prediction.
pub fn run_edge_infer(
    model: &PathPredictionModel,
    buf: &mut InferenceBuffer,
    telemetry: &[f32; INPUT_DIM],
) -> [f32; OUTPUT_DIM] {
    let raw = model.infer(telemetry.as_slice());
    buf.push(raw);
    let smoothed = buf.smoothed_output().unwrap_or_else(|| vec![0.0; OUTPUT_DIM]);
    let mut out = [0.0_f32; OUTPUT_DIM];
    out.copy_from_slice(&smoothed[..OUTPUT_DIM]);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn phase_marker_is_522() {
        assert_eq!(PHASE_MARKER, 522);
    }

    #[test]
    fn quantize_roundtrip_within_tolerance() {
        let layer = QuantizedLayer::quantize(&[1.0, -0.5, 0.25], &[0.0], 1, 3);
        // Dequantized values should be close to original
        let d0 = layer.dequantize_weight(0);
        assert!((d0 - 1.0).abs() < 0.02, "int8 quantize roundtrip error too large: {d0}");
    }

    #[test]
    fn infer_produces_correct_output_dimension() {
        let model = PathPredictionModel::new_stub();
        let input = [0.1_f32; INPUT_DIM];
        let output = model.infer(&input);
        assert_eq!(output.len(), OUTPUT_DIM);
    }

    #[test]
    fn inference_buffer_smoothing() {
        let mut buf = InferenceBuffer::new(3);
        buf.push(vec![1.0, 2.0]);
        buf.push(vec![3.0, 4.0]);
        let s = buf.smoothed_output().unwrap();
        assert!((s[0] - 2.0).abs() < 1e-5);
    }
}
