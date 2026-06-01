// Phase 524: Formation GAN Engine — 군집 편대 GAN 생성 엔진 (C++)
// Generative Adversarial Network for drone formation pattern synthesis.
#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <string>
#include <algorithm>
#include <numeric>

const int PHASE = 524;

// ── Activation functions ──────────────────────────────────────────

inline double relu(double x) { return x > 0 ? x : 0; }
inline double sigmoid(double x) { return 1.0 / (1.0 + std::exp(-x)); }
inline double tanh_act(double x) { return std::tanh(x); }

// ── Simple dense layer ────────────────────────────────────────────

struct DenseLayer {
    int in_dim, out_dim;
    std::vector<std::vector<double>> W;
    std::vector<double> b;

    DenseLayer(int in_d, int out_d, std::mt19937& rng) : in_dim(in_d), out_dim(out_d) {
        std::normal_distribution<double> nd(0.0, 0.1);
        W.resize(out_d, std::vector<double>(in_d));
        b.resize(out_d, 0.0);
        for (auto& row : W)
            for (auto& v : row) v = nd(rng);
    }

    std::vector<double> forward(const std::vector<double>& x,
                                const std::string& act = "relu") const {
        std::vector<double> out(out_dim, 0.0);
        for (int i = 0; i < out_dim; i++) {
            for (int j = 0; j < in_dim; j++) out[i] += W[i][j] * x[j];
            out[i] += b[i];
            if      (act == "relu")    out[i] = relu(out[i]);
            else if (act == "sigmoid") out[i] = sigmoid(out[i]);
            else if (act == "tanh")    out[i] = tanh_act(out[i]);
        }
        return out;
    }
};

// ── Generator ─────────────────────────────────────────────────────

/// Generator maps latent noise → formation coordinates.
class Generator {
public:
    DenseLayer l1, l2, l3;
    int latent_dim, output_dim;

    Generator(int latent_d, int out_d, std::mt19937& rng)
        : l1(latent_d, 64, rng), l2(64, 128, rng), l3(128, out_d, rng),
          latent_dim(latent_d), output_dim(out_d) {}

    std::vector<double> generate(const std::vector<double>& z) const {
        auto h1 = l1.forward(z, "relu");
        auto h2 = l2.forward(h1, "relu");
        auto out = l3.forward(h2, "tanh");
        return out;
    }
};

// ── Discriminator ─────────────────────────────────────────────────

/// Discriminator classifies real vs generated formations.
class Discriminator {
public:
    DenseLayer l1, l2, l3;

    Discriminator(int input_dim, std::mt19937& rng)
        : l1(input_dim, 128, rng), l2(128, 64, rng), l3(64, 1, rng) {}

    double classify(const std::vector<double>& x) const {
        auto h1 = l1.forward(x, "relu");
        auto h2 = l2.forward(h1, "relu");
        auto out = l3.forward(h2, "sigmoid");
        return out[0];
    }
};

// ── Formation GAN ─────────────────────────────────────────────────

class FormationGANEngine {
public:
    Generator gen;
    Discriminator disc;
    std::mt19937 rng;
    int latent_dim;
    int n_drones;
    std::vector<double> gen_losses;
    std::vector<double> disc_losses;

    FormationGANEngine(int n_drones, int latent_d, unsigned int seed)
        : gen(latent_d, n_drones * 3, rng),
          disc(n_drones * 3, rng),
          rng(seed), latent_dim(latent_d), n_drones(n_drones) {}

    std::vector<double> sample_noise() {
        std::normal_distribution<double> nd(0, 1);
        std::vector<double> z(latent_dim);
        for (auto& v : z) v = nd(rng);
        return z;
    }

    std::vector<double> sample_real_formation() {
        // Circular formation
        std::vector<double> form;
        for (int i = 0; i < n_drones; i++) {
            double angle = 2 * M_PI * i / n_drones;
            form.push_back(std::cos(angle) * 20.0);
            form.push_back(std::sin(angle) * 20.0);
            form.push_back(50.0);
        }
        return form;
    }

    void train_step() {
        // Generator forward
        auto z = sample_noise();
        auto fake = gen.generate(z);
        double d_fake = disc.classify(fake);
        double gen_loss = -std::log(d_fake + 1e-8);
        gen_losses.push_back(gen_loss);

        // Discriminator forward
        auto real = sample_real_formation();
        double d_real = disc.classify(real);
        double disc_loss = -std::log(d_real + 1e-8) - std::log(1.0 - d_fake + 1e-8);
        disc_losses.push_back(disc_loss);
    }

    void train(int epochs) {
        for (int e = 0; e < epochs; e++) train_step();
    }

    double avg_gen_loss() const {
        if (gen_losses.empty()) return 0.0;
        return std::accumulate(gen_losses.begin(), gen_losses.end(), 0.0) / gen_losses.size();
    }
};

int main() {
    std::cout << "Phase " << PHASE << ": Formation GAN Engine — 드론 편대 생성 GAN\n";
    FormationGANEngine gan(8, 16, 42);
    gan.train(20);
    std::cout << "Trained " << gan.gen_losses.size() << " steps, "
              << "avg gen_loss=" << gan.avg_gen_loss() << "\n";
    // Test generation
    auto z = gan.sample_noise();
    auto formation = gan.gen.generate(z);
    std::cout << "Generated formation coords: " << formation.size() << " values\n";
    return 0;
}
