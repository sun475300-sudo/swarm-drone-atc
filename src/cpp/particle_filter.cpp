// SDACS Particle Filter — C++
// 군집드론 파티클 필터 위치 추정

#include <vector>
#include <random>
#include <cmath>
#include <iostream>
#include <algorithm>
#include <numeric>

struct Particle {
    double x, y, z;
    double vx, vy, vz;
    double weight;
};

class ParticleFilter {
public:
    int n_particles;
    std::vector<Particle> particles;
    std::mt19937 rng;

    ParticleFilter(int n, double init_x, double init_y, double init_z)
        : n_particles(n), rng(std::random_device{}()) {
        particles.resize(n);
        std::normal_distribution<double> noise(0.0, 5.0);
        for (auto& p : particles) {
            p.x = init_x + noise(rng);
            p.y = init_y + noise(rng);
            p.z = init_z + noise(rng);
            p.vx = p.vy = p.vz = 0.0;
            p.weight = 1.0 / n;
        }
    }

    void predict(double dt, double noise_std = 0.5) {
        std::normal_distribution<double> noise(0.0, noise_std);
        for (auto& p : particles) {
            p.x += p.vx * dt + noise(rng);
            p.y += p.vy * dt + noise(rng);
            p.z += p.vz * dt + noise(rng);
        }
    }

    void update(double meas_x, double meas_y, double meas_z, double sigma = 2.0) {
        double sum_w = 0.0;
        for (auto& p : particles) {
            double dx = p.x - meas_x, dy = p.y - meas_y, dz = p.z - meas_z;
            double dist2 = dx*dx + dy*dy + dz*dz;
            p.weight = std::exp(-dist2 / (2.0 * sigma * sigma));
            sum_w += p.weight;
        }
        if (sum_w > 1e-12)
            for (auto& p : particles)
                p.weight /= sum_w;
    }

    void resample() {
        std::vector<double> cumulative(n_particles);
        cumulative[0] = particles[0].weight;
        for (int i = 1; i < n_particles; ++i)
            cumulative[i] = cumulative[i-1] + particles[i].weight;

        std::uniform_real_distribution<double> dist(0.0, 1.0);
        std::vector<Particle> new_particles(n_particles);
        for (auto& np : new_particles) {
            double r = dist(rng);
            auto it = std::lower_bound(cumulative.begin(), cumulative.end(), r);
            int idx = (int)(it - cumulative.begin());
            np = particles[std::min(idx, n_particles-1)];
            np.weight = 1.0 / n_particles;
        }
        particles = new_particles;
    }

    std::tuple<double,double,double> estimate() const {
        double ex = 0, ey = 0, ez = 0;
        for (const auto& p : particles) {
            ex += p.weight * p.x;
            ey += p.weight * p.y;
            ez += p.weight * p.z;
        }
        return {ex, ey, ez};
    }
};

int main() {
    ParticleFilter pf(500, 100.0, 200.0, 50.0);
    pf.predict(0.1);
    pf.update(102.0, 201.0, 50.5);
    pf.resample();
    auto [x, y, z] = pf.estimate();
    std::cout << "Estimated position: (" << x << ", " << y << ", " << z << ")\n";
    return 0;
}
