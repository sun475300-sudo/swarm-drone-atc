// Particle filter stub for SDACS state estimation — C++17
#include <vector>
#include <random>
#include <numeric>
#include <cmath>

struct Particle {
    double x, y, z;
    double weight;
};

class ParticleFilter {
public:
    explicit ParticleFilter(int n_particles, unsigned seed = 42)
        : rng_(seed) {
        particles_.resize(n_particles, {0.0, 0.0, 0.0, 1.0 / n_particles});
    }

    void predict(double dx, double dy, double dz, double noise_std) {
        std::normal_distribution<double> noise(0.0, noise_std);
        for (auto& p : particles_) {
            p.x += dx + noise(rng_);
            p.y += dy + noise(rng_);
            p.z += dz + noise(rng_);
        }
    }

    std::tuple<double, double, double> estimate() const {
        double x = 0, y = 0, z = 0, w = 0;
        for (const auto& p : particles_) { x += p.x * p.weight; y += p.y * p.weight; z += p.z * p.weight; w += p.weight; }
        return {x / w, y / w, z / w};
    }

private:
    std::vector<Particle> particles_;
    std::mt19937 rng_;
};
