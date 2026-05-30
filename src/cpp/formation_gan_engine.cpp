// Phase 524: formation_gan_engine — C++ 기반 편대 GAN 엔진
// SDACS Formation GAN Engine for Swarm Shape Generation

#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <random>
#include <algorithm>
#include <string>

// 2D 드론 위치 벡터
struct DronePos {
    float x, y, z;
};

// Generator: 노이즈 벡터 → 드론 편대 형상 생성
class Generator {
public:
    int latent_dim;
    int n_drones;

    Generator(int latent_dim, int n_drones)
        : latent_dim(latent_dim), n_drones(n_drones) {}

    // 잠재 벡터에서 드론 위치 생성
    std::vector<DronePos> generate(const std::vector<float>& z, std::mt19937& rng) const {
        std::vector<DronePos> formation(n_drones);
        std::normal_distribution<float> noise(0.0f, 0.1f);

        for (int i = 0; i < n_drones; i++) {
            float angle = 2.0f * M_PI * i / n_drones;
            float radius = z[0] * 10.0f + 5.0f;
            float altitude_spread = z[1] * 5.0f;
            formation[i] = {
                radius * std::cos(angle) + noise(rng),
                radius * std::sin(angle) + noise(rng),
                50.0f + altitude_spread * (i % 3) + noise(rng)
            };
        }
        return formation;
    }

    std::string name() const { return "FormationGenerator_v1"; }
};

// Discriminator: 드론 편대 → 실제/생성 분류
class Discriminator {
public:
    float threshold;
    int n_drones;

    Discriminator(int n_drones, float threshold = 0.5f)
        : n_drones(n_drones), threshold(threshold) {}

    // 편대 형상의 "실제" 점수 계산 (0=가짜, 1=실제)
    float discriminate(const std::vector<DronePos>& formation) const {
        if (formation.empty()) return 0.0f;

        // 무게중심 계산
        float cx = 0, cy = 0, cz = 0;
        for (const auto& d : formation) { cx += d.x; cy += d.y; cz += d.z; }
        cx /= formation.size(); cy /= formation.size(); cz /= formation.size();

        // 평균 거리 (편대 품질 지표)
        float avg_dist = 0.0f;
        for (const auto& d : formation) {
            float dx = d.x - cx, dy = d.y - cy, dz = d.z - cz;
            avg_dist += std::sqrt(dx*dx + dy*dy + dz*dz);
        }
        avg_dist /= formation.size();

        // 정규화된 품질 점수
        float score = 1.0f / (1.0f + std::exp(-avg_dist / 10.0f + 2.0f));
        return score;
    }

    bool classify(const std::vector<DronePos>& formation) const {
        return discriminate(formation) > threshold;
    }

    std::string name() const { return "FormationDiscriminator_v1"; }
};

// GAN 훈련 루프
class FormationGAN {
public:
    Generator generator;
    Discriminator discriminator;
    int iteration;

    FormationGAN(int latent_dim, int n_drones)
        : generator(latent_dim, n_drones),
          discriminator(n_drones),
          iteration(0) {}

    // GAN 생성 + 판별 단일 단계
    float trainStep(std::mt19937& rng) {
        std::uniform_real_distribution<float> uniform(-1.0f, 1.0f);
        std::vector<float> z(generator.latent_dim);
        for (auto& v : z) v = uniform(rng);

        auto formation = generator.generate(z, rng);
        float d_score = discriminator.discriminate(formation);
        iteration++;
        return d_score;
    }

    void train(int epochs, unsigned seed = 42) {
        std::mt19937 rng(seed);
        float total_score = 0.0f;
        for (int e = 0; e < epochs; e++) {
            total_score += trainStep(rng);
        }
        std::cout << "  훈련 완료 (" << epochs << " epochs), 평균 D 점수: "
                  << total_score / epochs << "\n";
    }
};

int main() {
    std::cout << "SDACS Formation GAN Engine — Phase 524\n\n";

    const int LATENT_DIM = 8;
    const int N_DRONES = 10;

    FormationGAN gan(LATENT_DIM, N_DRONES);
    std::cout << "Generator: " << gan.generator.name() << "\n";
    std::cout << "Discriminator: " << gan.discriminator.name() << "\n\n";

    std::cout << "GAN 훈련 시작...\n";
    gan.train(50);

    // 최종 편대 생성
    std::mt19937 rng(99);
    std::uniform_real_distribution<float> ud(-1.0f, 1.0f);
    std::vector<float> z(LATENT_DIM);
    for (auto& v : z) v = ud(rng);
    auto formation = gan.generator.generate(z, rng);

    std::cout << "\n생성된 편대 (" << N_DRONES << "대):\n";
    for (int i = 0; i < (int)formation.size(); i++) {
        std::cout << "  드론 " << i << ": ("
                  << formation[i].x << ", "
                  << formation[i].y << ", "
                  << formation[i].z << ")\n";
    }

    float q = gan.discriminator.discriminate(formation);
    bool real = gan.discriminator.classify(formation);
    std::cout << "\nDiscriminator 판별: " << (real ? "실제" : "생성") << " (점수=" << q << ")\n";
    std::cout << "Formation GAN 처리 완료.\n";
    return 0;
}
