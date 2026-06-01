// Phase 643: Particle Filter — 드론 위치 추적 파티클 필터 (C++)
// Sequential Monte Carlo particle filter for drone pose estimation.
#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <numeric>
#include <algorithm>

constexpr int NUM_PARTICLES = 500;
constexpr double PROCESS_NOISE = 0.5;
constexpr double MEASUREMENT_NOISE = 1.0;
constexpr int PHASE = 643;

/// Particle represents a hypothesis about drone state [x, y, z, yaw].
struct Particle {
    double x, y, z, yaw;
    double weight;
};

/// Measurement from GPS/IMU.
struct Measurement {
    double x, y, z;
};

/// ParticleFilter implements SIR (Sequential Importance Resampling).
class ParticleFilter {
public:
    std::vector<Particle> particles;
    std::mt19937 rng;
    std::normal_distribution<double> process_noise;
    std::normal_distribution<double> meas_noise;

    ParticleFilter(int n_particles, unsigned int seed)
        : rng(seed),
          process_noise(0.0, PROCESS_NOISE),
          meas_noise(0.0, MEASUREMENT_NOISE) {
        particles.resize(n_particles);
        std::uniform_real_distribution<double> init(-50.0, 50.0);
        for (auto& p : particles) {
            p.x = init(rng); p.y = init(rng); p.z = 50.0 + init(rng) * 0.5;
            p.yaw = 0.0;
            p.weight = 1.0 / n_particles;
        }
    }

    /// Propagate particles using a motion model.
    void predict(double vx, double vy, double vz, double dt) {
        for (auto& p : particles) {
            p.x += vx * dt + process_noise(rng);
            p.y += vy * dt + process_noise(rng);
            p.z += vz * dt + process_noise(rng) * 0.3;
        }
    }

    /// Update particle weights from measurement likelihood.
    void update(const Measurement& meas) {
        double sum = 0.0;
        for (auto& p : particles) {
            double dx = p.x - meas.x;
            double dy = p.y - meas.y;
            double dz = p.z - meas.z;
            double dist2 = dx*dx + dy*dy + dz*dz;
            double sigma2 = MEASUREMENT_NOISE * MEASUREMENT_NOISE;
            p.weight = std::exp(-0.5 * dist2 / sigma2);
            sum += p.weight;
        }
        // Normalize weights
        if (sum > 1e-10) {
            for (auto& p : particles) p.weight /= sum;
        }
    }

    /// Resample particles using systematic resampling.
    void resample() {
        std::vector<double> cumsum(particles.size());
        cumsum[0] = particles[0].weight;
        for (size_t i = 1; i < particles.size(); i++)
            cumsum[i] = cumsum[i-1] + particles[i].weight;

        std::uniform_real_distribution<double> udist(0.0, 1.0 / particles.size());
        double r = udist(rng);
        std::vector<Particle> new_particles;
        new_particles.reserve(particles.size());
        size_t j = 0;
        for (size_t i = 0; i < particles.size(); i++) {
            double threshold = r + static_cast<double>(i) / particles.size();
            while (j < particles.size() - 1 && cumsum[j] < threshold) j++;
            new_particles.push_back(particles[j]);
            new_particles.back().weight = 1.0 / particles.size();
        }
        particles = new_particles;
    }

    /// Compute weighted mean estimate.
    std::array<double, 3> estimate() const {
        double ex = 0, ey = 0, ez = 0;
        for (const auto& p : particles) {
            ex += p.weight * p.x;
            ey += p.weight * p.y;
            ez += p.weight * p.z;
        }
        return {ex, ey, ez};
    }

    /// Compute effective sample size (ESS).
    double ess() const {
        double sum2 = 0;
        for (const auto& p : particles) sum2 += p.weight * p.weight;
        return (sum2 > 0) ? 1.0 / sum2 : 0.0;
    }
};

int main() {
    std::cout << "Phase " << PHASE << ": Particle Filter — 드론 파티클 필터 위치 추정\n";
    ParticleFilter pf(NUM_PARTICLES, 42);
    std::mt19937 rng(42);
    std::normal_distribution<double> noise(0.0, 0.5);

    double true_x = 0.0, true_y = 0.0, true_z = 50.0;
    double total_error = 0.0;
    int steps = 30;

    for (int t = 0; t < steps; t++) {
        double vx = 1.0, vy = 0.5, vz = 0.0;
        true_x += vx * 0.1; true_y += vy * 0.1;
        pf.predict(vx, vy, vz, 0.1);
        Measurement meas{true_x + noise(rng), true_y + noise(rng), true_z + noise(rng)};
        pf.update(meas);
        pf.resample();
        auto est = pf.estimate();
        double err = std::sqrt(std::pow(est[0]-true_x,2)+std::pow(est[1]-true_y,2));
        total_error += err;
    }

    std::cout << "Avg position error: " << total_error / steps << " m\n";
    std::cout << "ESS: " << pf.ess() << "\n";
    return 0;
}
