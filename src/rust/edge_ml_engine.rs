// Phase 522: Rust Edge ML Engine — INT8 Quantization & Inference

struct PRNG { state: u64 }

impl PRNG {
    fn new(seed: u64) -> Self { Self { state: seed ^ 0x6c62272e07bb0142 } }
    fn next(&mut self) -> u64 {
        self.state ^= self.state << 13;
        self.state ^= self.state >> 7;
        self.state ^= self.state << 17;
        self.state
    }
    fn f64(&mut self) -> f64 { (self.next() & 0x7FFFFFFF) as f64 / 0x7FFFFFFF as f64 }
    fn normal(&mut self) -> f64 {
        let u1 = self.f64().max(1e-10);
        let u2 = self.f64();
        (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos()
    }
}

#[derive(Clone, Copy, PartialEq)]
enum ModelFormat { Float32, Float16, Int8, Int4 }

struct EdgeModel {
    name: String,
    format: ModelFormat,
    weights: Vec<f64>,
    bias: Vec<f64>,
    input_dim: usize,
    output_dim: usize,
    accuracy: f64,
    latency_ms: f64,
}

struct InferenceResult {
    output: Vec<f64>,
    latency_ms: f64,
    confidence: f64,
}

fn quantize_model(model: &EdgeModel, target: ModelFormat) -> EdgeModel {
    let acc_scale = match target {
        ModelFormat::Float16 => 0.99,
        ModelFormat::Int8 => 0.95,
        ModelFormat::Int4 => 0.88,
        _ => 1.0,
    };
    let speed_scale = match target {
        ModelFormat::Float16 => 0.7,
        ModelFormat::Int8 => 0.4,
        ModelFormat::Int4 => 0.25,
        _ => 1.0,
    };
    let weights: Vec<f64> = match target {
        ModelFormat::Int8 => model.weights.iter().map(|w| (w * 127.0).round() / 127.0).collect(),
        ModelFormat::Int4 => model.weights.iter().map(|w| (w * 7.0).round() / 7.0).collect(),
        _ => model.weights.clone(),
    };
    EdgeModel {
        name: format!("{}_q{:?}", model.name, target as u8),
        format: target,
        weights, bias: model.bias.clone(),
        input_dim: model.input_dim, output_dim: model.output_dim,
        accuracy: model.accuracy * acc_scale,
        latency_ms: model.latency_ms * speed_scale,
    }
}

fn infer(model: &EdgeModel, input: &[f64], rng: &mut PRNG) -> InferenceResult {
    let mut output = vec![0.0; model.output_dim];
    for j in 0..model.output_dim {
        let mut sum = model.bias[j];
        for i in 0..model.input_dim.min(input.len()) {
            let w_idx = i * model.output_dim + j;
            if w_idx < model.weights.len() {
                sum += input[i] * model.weights[w_idx];
            }
        }
        output[j] = 1.0 / (1.0 + (-sum).exp()); // sigmoid
    }
    let confidence = output.iter().cloned().fold(0.0_f64, f64::max);
    let latency = model.latency_ms + rng.f64() * 0.5;
    InferenceResult { output, latency_ms: latency, confidence }
}

fn main() {
    let mut rng = PRNG::new(42);
    let dim_in = 10;
    let dim_out = 3;
    let weights: Vec<f64> = (0..dim_in * dim_out).map(|_| rng.normal() * 0.1).collect();
    let bias: Vec<f64> = (0..dim_out).map(|_| rng.normal() * 0.01).collect();

    let model = EdgeModel {
        name: "detector_0".into(), format: ModelFormat::Float32,
        weights, bias, input_dim: dim_in, output_dim: dim_out,
        accuracy: 0.95, latency_ms: 5.0,
    };

    let q_model = quantize_model(&model, ModelFormat::Int8);
    println!("Original: acc={:.4} lat={:.1}ms", model.accuracy, model.latency_ms);
    println!("INT8:     acc={:.4} lat={:.1}ms", q_model.accuracy, q_model.latency_ms);

    let input: Vec<f64> = (0..dim_in).map(|_| rng.normal()).collect();
    let result = infer(&q_model, &input, &mut rng);
    println!("Inference: conf={:.4} lat={:.2}ms out_len={}", result.confidence, result.latency_ms, result.output.len());
}
