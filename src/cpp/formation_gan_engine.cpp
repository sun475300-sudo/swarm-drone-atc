// Phase 524: Formation GAN Engine — C++
// SDACS generative adversarial network for optimal drone formation generation

#include <vector>
#include <cmath>
#include <random>
#include <iostream>
#include <algorithm>
#include <stdexcept>
#include <string>

// Phase 524 marker — formation GAN with Generator and Discriminator

namespace sdacs {

using Vec = std::vector<float>;
using Mat = std::vector<Vec>;

// ============================================================
// Activation functions

inline float relu(float x) { return x > 0.0f ? x : 0.0f; }
inline float sigmoid(float x) { return 1.0f / (1.0f + std::exp(-x)); }
inline float tanh_act(float x) { return std::tanh(x); }

Vec apply_relu(const Vec& v) {
    Vec out(v.size());
    std::transform(v.begin(), v.end(), out.begin(), relu);
    return out;
}

Vec apply_sigmoid(const Vec& v) {
    Vec out(v.size());
    std::transform(v.begin(), v.end(), out.begin(), sigmoid);
    return out;
}

Vec apply_tanh(const Vec& v) {
    Vec out(v.size());
    std::transform(v.begin(), v.end(), out.begin(), tanh_act);
    return out;
}

// ============================================================
// Dense layer: y = W*x + b

class DenseLayer {
public:
    Mat weights;
    Vec bias;
    std::string activation;
    int in_size, out_size;

    DenseLayer(int in_sz, int out_sz, const std::string& act = "relu",
               unsigned seed = 42)
        : in_size(in_sz), out_size(out_sz), activation(act)
    {
        std::mt19937 rng(seed);
        std::normal_distribution<float> dist(0.0f, 0.1f);
        weights.resize(out_sz, Vec(in_sz));
        bias.resize(out_sz, 0.0f);
        for (auto& row : weights)
            for (auto& w : row) w = dist(rng);
    }

    Vec forward(const Vec& x) const {
        if ((int)x.size() != in_size)
            throw std::invalid_argument("Input size mismatch");
        Vec out(out_size, 0.0f);
        for (int i = 0; i < out_size; i++) {
            for (int j = 0; j < in_size; j++)
                out[i] += weights[i][j] * x[j];
            out[i] += bias[i];
        }
        if      (activation == "relu")    return apply_relu(out);
        else if (activation == "sigmoid") return apply_sigmoid(out);
        else if (activation == "tanh")    return apply_tanh(out);
        return out;  // linear
    }
};

// ============================================================
// Generator: noise vector → formation positions

class Generator {
public:
    std::vector<DenseLayer> layers;
    int noise_dim;
    int n_drones;

    explicit Generator(int n_drones = 10, int noise_dim = 32)
        : noise_dim(noise_dim), n_drones(n_drones)
    {
        layers.emplace_back(noise_dim, 64,       "relu",    101);
        layers.emplace_back(64,        128,       "relu",    102);
        layers.emplace_back(128,       64,        "relu",    103);
        layers.emplace_back(64,        n_drones*3,"tanh",    104);  // (x,y,z)*n
    }

    // Generate formation: returns [n_drones][x,y,z] positions
    std::vector<std::array<float,3>> generate(const Vec& noise) const {
        if ((int)noise.size() != noise_dim)
            throw std::invalid_argument("Noise dim mismatch");

        Vec h = noise;
        for (const auto& layer : layers) h = layer.forward(h);

        // Reshape flat output to positions
        std::vector<std::array<float,3>> positions(n_drones);
        for (int i = 0; i < n_drones; i++) {
            positions[i] = {
                h[i*3]   * 100.0f,  // x in [-100, 100] m
                h[i*3+1] * 100.0f,  // y in [-100, 100] m
                h[i*3+2] *  60.0f + 60.0f  // z in [0, 120] m
            };
        }
        return positions;
    }

    Vec sample_noise(unsigned seed = 0) const {
        std::mt19937 rng(seed);
        std::normal_distribution<float> dist(0.0f, 1.0f);
        Vec noise(noise_dim);
        for (auto& n : noise) n = dist(rng);
        return noise;
    }
};

// ============================================================
// Discriminator: formation positions → real/fake score

class Discriminator {
public:
    std::vector<DenseLayer> layers;
    int input_dim;
    int n_drones;

    explicit Discriminator(int n_drones = 10)
        : input_dim(n_drones * 3), n_drones(n_drones)
    {
        layers.emplace_back(input_dim, 128, "relu",    201);
        layers.emplace_back(128,        64,  "relu",    202);
        layers.emplace_back(64,         32,  "relu",    203);
        layers.emplace_back(32,          1,  "sigmoid", 204);
    }

    float discriminate(const std::vector<std::array<float,3>>& positions) const {
        Vec flat(n_drones * 3);
        for (int i = 0; i < n_drones; i++) {
            flat[i*3]   = positions[i][0] / 100.0f;
            flat[i*3+1] = positions[i][1] / 100.0f;
            flat[i*3+2] = (positions[i][2] - 60.0f) / 60.0f;
        }
        Vec h = flat;
        for (const auto& layer : layers) h = layer.forward(h);
        return h[0];  // probability of real
    }
};

// ============================================================
// GAN orchestrator

class FormationGAN {
public:
    Generator    generator;
    Discriminator discriminator;
    int n_drones;

    explicit FormationGAN(int n_drones = 10)
        : generator(n_drones), discriminator(n_drones), n_drones(n_drones) {}

    // Generate an optimal formation
    std::vector<std::array<float,3>> generate_formation(unsigned seed = 0) const {
        auto noise = generator.sample_noise(seed);
        return generator.generate(noise);
    }

    // Score how "real" (good) a formation looks
    float score_formation(const std::vector<std::array<float,3>>& positions) const {
        return discriminator.discriminate(positions);
    }

    // Find best formation from multiple samples
    std::vector<std::array<float,3>> best_formation(int n_samples = 10) const {
        float best_score = -1.0f;
        std::vector<std::array<float,3>> best;

        for (int i = 0; i < n_samples; i++) {
            auto f = generate_formation(i * 137);
            float score = score_formation(f);
            if (score > best_score) {
                best_score = score;
                best = f;
            }
        }
        return best;
    }
};

}  // namespace sdacs

int main() {
    sdacs::FormationGAN gan(8);
    auto formation = gan.best_formation(20);

    std::cout << "Phase 524: Formation GAN — Generated " << formation.size()
              << " drone positions:\n";
    for (size_t i = 0; i < formation.size(); i++) {
        std::cout << "  D" << i << ": ("
                  << formation[i][0] << ", "
                  << formation[i][1] << ", "
                  << formation[i][2] << ")\n";
    }

    float score = gan.score_formation(formation);
    std::cout << "Formation score: " << score << "\n";
    return 0;
}
