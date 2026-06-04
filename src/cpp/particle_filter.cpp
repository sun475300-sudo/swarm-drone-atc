// Phase 643: Particle Filter — C++
// SDACS Monte Carlo localization for GPS-denied drone navigation

#include <vector>
#include <cmath>
#include <random>
#include <numeric>
#include <algorithm>
#include <iostream>

namespace sdacs {

struct Particle {
    double x, y, z;
    double weight;
};

class ParticleFilter {
public:
    int    n_particles;
    double noise_pos;
    double noise_obs;
    std::vector<Particle> particles;
    std::mt19937 rng;

    ParticleFilter(int n = 500, double np = 1.0, double no = 2.0)
        : n_particles(n), noise_pos(np), noise_obs(no), rng(std::random_device{}())
    {
        particles.resize(n);
    }

    void init(double x0, double y0, double z0, double spread = 5.0) {
        std::normal_distribution<double> d(0, spread);
        for (auto& p : particles) {
            p.x      = x0 + d(rng);
            p.y      = y0 + d(rng);
            p.z      = z0 + d(rng);
            p.weight = 1.0 / n_particles;
        }
    }

    void predict(double dx, double dy, double dz) {
        std::normal_distribution<double> d(0, noise_pos);
        for (auto& p : particles) {
            p.x += dx + d(rng);
            p.y += dy + d(rng);
            p.z += dz + d(rng);
        }
    }

    void update(double obs_x, double obs_y, double obs_z) {
        double sum = 0;
        for (auto& p : particles) {
            double dx = p.x - obs_x, dy = p.y - obs_y, dz = p.z - obs_z;
            double dist = std::sqrt(dx*dx + dy*dy + dz*dz);
            p.weight = std::exp(-0.5 * (dist/noise_obs) * (dist/noise_obs));
            sum += p.weight;
        }
        if (sum > 1e-10) for (auto& p : particles) p.weight /= sum;
    }

    std::tuple<double,double,double> estimate() const {
        double x=0, y=0, z=0;
        for (const auto& p : particles) { x += p.x*p.weight; y += p.y*p.weight; z += p.z*p.weight; }
        return {x, y, z};
    }

    void resample() {
        std::uniform_real_distribution<double> d(0, 1.0/n_particles);
        double r = d(rng);
        std::vector<Particle> new_particles;
        new_particles.reserve(n_particles);
        double c = particles[0].weight;
        int i = 0;
        for (int m = 0; m < n_particles; m++) {
            double U = r + (double)m / n_particles;
            while (U > c) { i = (i+1) % n_particles; c += particles[i].weight; }
            new_particles.push_back(particles[i]);
            new_particles.back().weight = 1.0 / n_particles;
        }
        particles = std::move(new_particles);
    }
};

} // namespace sdacs

int main() {
    sdacs::ParticleFilter pf(500);
    pf.init(100.0, 200.0, 60.0, 3.0);
    pf.predict(5.0, 0.0, 0.0);
    pf.update(105.0, 200.5, 60.0);
    pf.resample();
    auto [x,y,z] = pf.estimate();
    std::cout << "Phase 643: Estimate (" << x << ", " << y << ", " << z << ")\n";
    return 0;
}
