// Phase 653 — Monte Carlo Particle Filter in C++
#include <vector>
#include <array>
#include <random>
#include <numeric>
#include <cmath>

struct Particle { std::array<double,3> pos; double weight; };

class ParticleFilter {
    std::mt19937 rng_;
    std::vector<Particle> particles_;
public:
    explicit ParticleFilter(int n, std::array<double,3> init, double noise=1.0)
        : rng_(42), particles_(n) {
        std::normal_distribution<> nd(0, noise);
        for (auto& p : particles_) {
            p.pos = {init[0]+nd(rng_), init[1]+nd(rng_), init[2]+nd(rng_)};
            p.weight = 1.0 / n;
        }
    }

    void predict(std::array<double,3> motion, double noise=0.5) {
        std::normal_distribution<> nd(0, noise);
        for (auto& p : particles_)
            for (int i=0; i<3; ++i) p.pos[i] += motion[i] + nd(rng_);
    }

    void update(std::array<double,3> obs, double sigma=1.0) {
        double total = 0;
        for (auto& p : particles_) {
            double d2 = 0;
            for (int i=0; i<3; ++i) d2 += std::pow(p.pos[i]-obs[i], 2);
            p.weight = std::exp(-d2/(2*sigma*sigma));
            total += p.weight;
        }
        for (auto& p : particles_) p.weight /= total;
    }

    std::array<double,3> estimate() const {
        std::array<double,3> est{0,0,0};
        for (const auto& p : particles_)
            for (int i=0; i<3; ++i) est[i] += p.weight * p.pos[i];
        return est;
    }
};
