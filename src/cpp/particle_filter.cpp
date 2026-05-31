// Particle Filter — SDACS Phase 653
#include <vector>
#include <random>
#include <cmath>

struct Particle {
    double lat, lon, alt, weight;
};

class ParticleFilter {
    std::vector<Particle> particles_;
    std::mt19937 rng_;
public:
    ParticleFilter(int n, unsigned seed = 42) : rng_(seed) {
        particles_.resize(n, {0, 0, 0, 1.0 / n});
    }
    void update(double lat, double lon, double alt) {
        for (auto& p : particles_) {
            p.lat += lat; p.lon += lon; p.alt += alt;
        }
    }
    size_t size() const { return particles_.size(); }
};
