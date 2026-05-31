// particle_filter.cpp - Particle filter for drone state estimation
#include <vector>
#include <cmath>
#include <random>
#include <numeric>
#include <algorithm>

struct Particle {
    double x, y, z;
    double vx, vy, vz;
    double weight;
};

struct Measurement {
    double x, y, z;
    double noise_std;
};

class ParticleFilter {
public:
    int n_particles;
    std::vector<Particle> particles;
    std::mt19937 rng;
    double process_noise;
    double obs_noise;

    ParticleFilter(int n, unsigned seed = 42)
        : n_particles(n), rng(seed), process_noise(0.5), obs_noise(1.0) {
        particles.resize(n);
        std::normal_distribution<double> pos_dist(0.0, 100.0);
        std::normal_distribution<double> vel_dist(0.0, 5.0);
        for (auto& p : particles) {
            p.x = pos_dist(rng); p.y = pos_dist(rng); p.z = 50.0 + pos_dist(rng) * 0.1;
            p.vx = vel_dist(rng); p.vy = vel_dist(rng); p.vz = 0.0;
            p.weight = 1.0 / n;
        }
    }

    void predict(double dt) {
        std::normal_distribution<double> noise(0.0, process_noise);
        for (auto& p : particles) {
            p.x += p.vx * dt + noise(rng);
            p.y += p.vy * dt + noise(rng);
            p.z += p.vz * dt + noise(rng) * 0.1;
        }
    }

    void update(const Measurement& meas) {
        double sum_w = 0.0;
        for (auto& p : particles) {
            double dx = p.x - meas.x, dy = p.y - meas.y, dz = p.z - meas.z;
            double dist2 = dx*dx + dy*dy + dz*dz;
            p.weight = std::exp(-dist2 / (2.0 * obs_noise * obs_noise));
            sum_w += p.weight;
        }
        for (auto& p : particles) p.weight /= sum_w;
    }

    Particle estimate() const {
        Particle est{0,0,0,0,0,0,0};
        for (const auto& p : particles) {
            est.x += p.x * p.weight; est.y += p.y * p.weight; est.z += p.z * p.weight;
        }
        return est;
    }

    void resample() {
        std::vector<Particle> new_particles;
        new_particles.reserve(n_particles);
        std::uniform_real_distribution<double> u(0.0, 1.0 / n_particles);
        double c = particles[0].weight;
        int i = 0;
        double r = u(rng);
        for (int m = 0; m < n_particles; m++) {
            double U = r + static_cast<double>(m) / n_particles;
            while (U > c) { i++; c += particles[i % n_particles].weight; }
            new_particles.push_back(particles[i % n_particles]);
        }
        particles = std::move(new_particles);
        for (auto& p : particles) p.weight = 1.0 / n_particles;
    }
};
