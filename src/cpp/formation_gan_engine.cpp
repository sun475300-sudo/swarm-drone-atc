// SDACS Formation GAN Engine — C++ (Phase 524)
// 드론 편대 생성 GAN (Generator + Discriminator)

#include <cmath>
#include <vector>
#include <string>
#include <random>
#include <functional>
#include <stdexcept>

namespace sdacs {

using Vec = std::vector<double>;
using Matrix = std::vector<Vec>;

// 활성화 함수
static double relu(double x) { return x > 0.0 ? x : 0.0; }
static double sigmoid(double x) { return 1.0 / (1.0 + std::exp(-x)); }
static double tanh_(double x) { return std::tanh(x); }

// 간단한 선형 레이어
class LinearLayer {
public:
    Matrix W;
    Vec b;
    std::size_t in_dim, out_dim;

    LinearLayer(std::size_t in, std::size_t out, std::mt19937& rng)
        : in_dim(in), out_dim(out), W(out, Vec(in)), b(out, 0.0)
    {
        std::normal_distribution<double> dist(0.0, 0.02);
        for (auto& row : W)
            for (auto& w : row)
                w = dist(rng);
    }

    Vec forward(const Vec& x) const {
        Vec out(out_dim, 0.0);
        for (std::size_t j = 0; j < out_dim; ++j) {
            for (std::size_t i = 0; i < in_dim; ++i)
                out[j] += W[j][i] * x[i];
            out[j] += b[j];
        }
        return out;
    }
};

// ─── Generator (Phase 524) ─────────────────────────────────────────────────
class Generator {
    LinearLayer fc1, fc2, fc_out;
    std::size_t latent_dim, output_dim;
public:
    Generator(std::size_t latent, std::size_t out, std::mt19937& rng)
        : fc1(latent, 128, rng), fc2(128, 64, rng), fc_out(64, out, rng)
        , latent_dim(latent), output_dim(out)
    {}

    // 편대 좌표 생성 (latent noise → formation positions)
    Vec generate(const Vec& z) const {
        auto h1 = fc1.forward(z);
        for (auto& v : h1) v = relu(v);

        auto h2 = fc2.forward(h1);
        for (auto& v : h2) v = relu(v);

        auto out = fc_out.forward(h2);
        for (auto& v : out) v = tanh_(v) * 100.0;  // scale to meters
        return out;
    }

    Vec sampleNoise(std::mt19937& rng) const {
        std::normal_distribution<double> dist(0.0, 1.0);
        Vec z(latent_dim);
        for (auto& v : z) v = dist(rng);
        return z;
    }

    std::size_t latentDim() const { return latent_dim; }
    std::size_t outputDim() const { return output_dim; }
};

// ─── Discriminator ──────────────────────────────────────────────────────────
class Discriminator {
    LinearLayer fc1, fc2, fc_out;
public:
    Discriminator(std::size_t input_dim, std::mt19937& rng)
        : fc1(input_dim, 64, rng), fc2(64, 32, rng), fc_out(32, 1, rng)
    {}

    // 편대 패턴 진위 판별 → [0, 1]
    double discriminate(const Vec& x) const {
        auto h1 = fc1.forward(x);
        for (auto& v : h1) v = relu(v);

        auto h2 = fc2.forward(h1);
        for (auto& v : h2) v = relu(v);

        auto out = fc_out.forward(h2);
        return sigmoid(out[0]);
    }
};

// ─── GAN 훈련 오케스트레이터 ──────────────────────────────────────────────
class FormationGANEngine {
    Generator gen;
    Discriminator disc;
    std::mt19937 rng;
    int n_drones;

public:
    FormationGANEngine(int n_drones, unsigned seed = 42)
        : gen(16, n_drones * 3, rng)    // 3D 좌표 × n_drones
        , disc(n_drones * 3, rng)
        , rng(seed)
        , n_drones(n_drones)
    {}

    // 편대 위치 벡터 생성
    Vec generateFormation() {
        auto z = gen.sampleNoise(rng);
        return gen.generate(z);
    }

    // 편대 진위 점수
    double scoreFormation(const Vec& positions) {
        return disc.discriminate(positions);
    }

    // 여러 편대 생성 후 최고 점수 선택
    Vec bestFormation(int candidates = 10) {
        Vec best;
        double best_score = -1.0;
        for (int i = 0; i < candidates; ++i) {
            auto f = generateFormation();
            double score = scoreFormation(f);
            if (score > best_score) {
                best_score = score;
                best = f;
            }
        }
        return best;
    }

    int droneCount() const { return n_drones; }
};

}  // namespace sdacs
