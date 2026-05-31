// P653: Particle Filter - C++ stub
// Particle filter for drone state estimation

#include <vector>
#include <random>
#include <numeric>
#include <cmath>
#include <array>

struct Particle {
    std::array<double, 3> position;
    std::array<double, 3> velocity;
    double weight;
};

class ParticleFilter {
public:
    explicit ParticleFilter(int n_particles = 1000)
        : n_particles_(n_particles), rng_(std::random_device{}()) {
        particles_.resize(n_particles);
    }

    void initialize(const std::array<double, 3>& pos, double noise_std) {
        std::normal_distribution<double> noise(0.0, noise_std);
        for (auto& p : particles_) {
            p.position = {pos[0] + noise(rng_), pos[1] + noise(rng_), pos[2] + noise(rng_)};
            p.velocity = {0.0, 0.0, 0.0};
            p.weight = 1.0 / n_particles_;
        }
    }

    void predict(const std::array<double, 3>& control, double dt, double noise_std) {
        std::normal_distribution<double> noise(0.0, noise_std);
        for (auto& p : particles_) {
            for (int i = 0; i < 3; i++) {
                p.velocity[i] = control[i];
                p.position[i] += p.velocity[i] * dt + noise(rng_);
            }
        }
    }

    void update(const std::array<double, 3>& measurement, double sensor_std) {
        double total_weight = 0.0;
        for (auto& p : particles_) {
            double dist_sq = 0.0;
            for (int i = 0; i < 3; i++) {
                double d = p.position[i] - measurement[i];
                dist_sq += d * d;
            }
            p.weight *= std::exp(-dist_sq / (2.0 * sensor_std * sensor_std));
            total_weight += p.weight;
        }
        for (auto& p : particles_) p.weight /= total_weight;
    }

    std::array<double, 3> estimate() const {
        std::array<double, 3> est = {0.0, 0.0, 0.0};
        for (const auto& p : particles_) {
            for (int i = 0; i < 3; i++) est[i] += p.weight * p.position[i];
        }
        return est;
    }

private:
    int n_particles_;
    std::vector<Particle> particles_;
    std::mt19937 rng_;
};
