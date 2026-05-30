// Phase 653 — C++ Particle Filter (Monte Carlo position estimation)
#include <vector>
#include <random>
#include <cmath>
#include <algorithm>

struct Particle { double x, y, z, weight; };

class ParticleFilter {
public:
    ParticleFilter(int n_particles, double noise_std = 0.5)
        : n_(n_particles), noise_(noise_std), rng_(42) {
        particles_.resize(n_);
        double w = 1.0 / n_particles;
        for (auto& p : particles_) { p = {0, 0, 0, w}; }
    }

    void predict(double dx, double dy, double dz) {
        std::normal_distribution<double> nd(0, noise_);
        for (auto& p : particles_) {
            p.x += dx + nd(rng_);
            p.y += dy + nd(rng_);
            p.z += dz + nd(rng_);
        }
    }

    void update(double obs_x, double obs_y, double obs_z) {
        for (auto& p : particles_) {
            double d = std::sqrt(std::pow(p.x-obs_x,2)+std::pow(p.y-obs_y,2)+std::pow(p.z-obs_z,2));
            p.weight = std::exp(-0.5 * d * d / (noise_ * noise_));
        }
        normalize();
    }

    std::array<double,3> estimate() {
        double sx=0, sy=0, sz=0;
        for (auto& p : particles_) { sx+=p.x*p.weight; sy+=p.y*p.weight; sz+=p.z*p.weight; }
        return {sx, sy, sz};
    }

private:
    int n_; double noise_; std::mt19937 rng_;
    std::vector<Particle> particles_;
    void normalize() {
        double sum = 0;
        for (auto& p : particles_) sum += p.weight;
        for (auto& p : particles_) p.weight /= sum;
    }
};
