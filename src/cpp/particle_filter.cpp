// Phase 653: Particle Filter — C++ Monte Carlo Localization
// 파티클 필터 기반 드론 위치 추정 (Monte Carlo Localization)

#include <vector>
#include <cmath>
#include <random>
#include <numeric>
#include <algorithm>
#include <iostream>
#include <iomanip>

struct Particle {
    double x, y, z;
    double weight;
};

struct Measurement {
    double x, y, z;
    double noise_std;
};

class ParticleFilter {
public:
    ParticleFilter(int n_particles, unsigned seed = 42)
        : n_particles_(n_particles), gen_(seed) {
        particles_.resize(n_particles);
    }

    void initialize(double cx, double cy, double cz, double spread) {
        std::normal_distribution<double> dist_x(cx, spread);
        std::normal_distribution<double> dist_y(cy, spread);
        std::normal_distribution<double> dist_z(cz, spread * 0.3);

        for (auto& p : particles_) {
            p.x = dist_x(gen_);
            p.y = dist_y(gen_);
            p.z = dist_z(gen_);
            p.weight = 1.0 / n_particles_;
        }
    }

    void predict(double dx, double dy, double dz, double noise) {
        std::normal_distribution<double> noise_dist(0.0, noise);
        for (auto& p : particles_) {
            p.x += dx + noise_dist(gen_);
            p.y += dy + noise_dist(gen_);
            p.z += dz + noise_dist(gen_) * 0.3;
        }
    }

    void update(const Measurement& meas) {
        double total_weight = 0.0;
        for (auto& p : particles_) {
            double dx = p.x - meas.x;
            double dy = p.y - meas.y;
            double dz = p.z - meas.z;
            double dist2 = dx*dx + dy*dy + dz*dz;
            double sigma2 = meas.noise_std * meas.noise_std;

            p.weight *= std::exp(-dist2 / (2.0 * sigma2));
            total_weight += p.weight;
        }

        // Normalize weights
        if (total_weight > 1e-15) {
            for (auto& p : particles_) {
                p.weight /= total_weight;
            }
        }
    }

    void resample() {
        std::vector<Particle> new_particles;
        new_particles.reserve(n_particles_);

        // Systematic resampling
        std::uniform_real_distribution<double> uni(0.0, 1.0 / n_particles_);
        double r = uni(gen_);
        double cumulative = particles_[0].weight;
        int i = 0;

        for (int j = 0; j < n_particles_; ++j) {
            double u = r + static_cast<double>(j) / n_particles_;
            while (u > cumulative && i < n_particles_ - 1) {
                ++i;
                cumulative += particles_[i].weight;
            }
            new_particles.push_back(particles_[i]);
            new_particles.back().weight = 1.0 / n_particles_;
        }

        particles_ = std::move(new_particles);
    }

    struct Estimate {
        double x, y, z;
        double variance;
    };

    Estimate estimate() const {
        double wx = 0, wy = 0, wz = 0;
        for (const auto& p : particles_) {
            wx += p.x * p.weight;
            wy += p.y * p.weight;
            wz += p.z * p.weight;
        }

        double var = 0;
        for (const auto& p : particles_) {
            double dx = p.x - wx;
            double dy = p.y - wy;
            double dz = p.z - wz;
            var += p.weight * (dx*dx + dy*dy + dz*dz);
        }

        return {wx, wy, wz, var};
    }

    double effective_sample_size() const {
        double sum_sq = 0;
        for (const auto& p : particles_) {
            sum_sq += p.weight * p.weight;
        }
        return 1.0 / std::max(sum_sq, 1e-15);
    }

private:
    int n_particles_;
    std::mt19937 gen_;
    std::vector<Particle> particles_;
};

int main() {
    ParticleFilter pf(500, 42);
    pf.initialize(0.0, 0.0, 60.0, 50.0);

    // Simulate drone moving with noisy measurements
    double true_x = 0, true_y = 0, true_z = 60;
    double vx = 5.0, vy = 3.0, vz = 0.0;
    std::mt19937 meas_gen(123);
    std::normal_distribution<double> meas_noise(0.0, 5.0);

    for (int step = 0; step < 50; ++step) {
        true_x += vx * 0.1;
        true_y += vy * 0.1;
        true_z += vz * 0.1;

        pf.predict(vx * 0.1, vy * 0.1, vz * 0.1, 2.0);

        Measurement m = {
            true_x + meas_noise(meas_gen),
            true_y + meas_noise(meas_gen),
            true_z + meas_noise(meas_gen) * 0.3,
            5.0
        };
        pf.update(m);

        if (pf.effective_sample_size() < 250) {
            pf.resample();
        }
    }

    auto est = pf.estimate();
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "True:     (" << true_x << ", " << true_y << ", " << true_z << ")\n";
    std::cout << "Estimate: (" << est.x << ", " << est.y << ", " << est.z << ")\n";
    std::cout << "Variance: " << est.variance << "\n";
    std::cout << "ESS:      " << pf.effective_sample_size() << "\n";

    return 0;
}
