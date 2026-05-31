// Phase 653 — Particle Filter (C++)
// 드론 위치 추정을 위한 파티클 필터 (SIR)

#include <algorithm>
#include <array>
#include <cmath>
#include <numeric>
#include <random>
#include <vector>

namespace sdacs {

struct Particle {
    std::array<double, 3> position;  // [x, y, z] metres
    std::array<double, 3> velocity;  // [vx, vy, vz] m/s
    double weight = 1.0;
};

/// SIR (Sequential Importance Resampling) 파티클 필터
class ParticleFilter {
public:
    explicit ParticleFilter(int n_particles = 1000, unsigned int seed = 42)
        : rng_(seed), n_particles_(n_particles) {
        particles_.resize(n_particles_);
        init_uniform({0.0, 0.0, 100.0}, 50.0);
    }

    /// 파티클을 위치 중심으로 균일 분포로 초기화한다.
    void init_uniform(std::array<double, 3> center, double spread) {
        std::uniform_real_distribution<double> dist(-spread, spread);
        for (auto& p : particles_) {
            p.position = {center[0] + dist(rng_),
                          center[1] + dist(rng_),
                          center[2] + dist(rng_) * 0.1};
            p.velocity = {0.0, 0.0, 0.0};
            p.weight = 1.0 / n_particles_;
        }
    }

    /// 운동 모델로 파티클을 전파한다.
    void predict(double dt, double process_noise = 0.5) {
        std::normal_distribution<double> noise(0.0, process_noise);
        for (auto& p : particles_) {
            for (int i = 0; i < 3; ++i) {
                p.position[i] += p.velocity[i] * dt + noise(rng_);
            }
        }
    }

    /// GPS 관측으로 파티클 가중치를 갱신한다.
    void update(std::array<double, 3> measurement, double meas_noise = 2.0) {
        double total = 0.0;
        for (auto& p : particles_) {
            double sq_dist = 0.0;
            for (int i = 0; i < 3; ++i) {
                double diff = p.position[i] - measurement[i];
                sq_dist += diff * diff;
            }
            p.weight *= std::exp(-sq_dist / (2.0 * meas_noise * meas_noise));
            total += p.weight;
        }
        // 정규화
        if (total > 1e-12) {
            for (auto& p : particles_) p.weight /= total;
        }
    }

    /// 가중 평균으로 위치를 추정한다.
    std::array<double, 3> estimate() const {
        std::array<double, 3> est = {0.0, 0.0, 0.0};
        for (const auto& p : particles_) {
            for (int i = 0; i < 3; ++i)
                est[i] += p.weight * p.position[i];
        }
        return est;
    }

    /// 체계적 리샘플링을 수행한다.
    void resample() {
        std::vector<double> cum(n_particles_);
        cum[0] = particles_[0].weight;
        for (int i = 1; i < n_particles_; ++i)
            cum[i] = cum[i - 1] + particles_[i].weight;

        std::uniform_real_distribution<double> u(0.0, 1.0 / n_particles_);
        double r = u(rng_);
        std::vector<Particle> new_particles(n_particles_);
        int idx = 0;
        for (int i = 0; i < n_particles_; ++i) {
            double target = r + static_cast<double>(i) / n_particles_;
            while (idx < n_particles_ - 1 && cum[idx] < target) ++idx;
            new_particles[i] = particles_[idx];
            new_particles[i].weight = 1.0 / n_particles_;
        }
        particles_ = std::move(new_particles);
    }

    int particle_count() const { return n_particles_; }

private:
    std::mt19937 rng_;
    int n_particles_;
    std::vector<Particle> particles_;
};

}  // namespace sdacs
