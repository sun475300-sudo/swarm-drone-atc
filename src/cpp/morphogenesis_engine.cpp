// Phase 494: Morphogenesis Engine (C++)
// 반응-확산 패턴 형성, Turing 패턴, 군집 형태발생

#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <array>
#include <string>

namespace morphogenesis {

enum class Formation { Circle, Line, VShape, Grid, Spiral, Ring };

struct Vec3 {
    double x, y, z;
    Vec3(double x = 0, double y = 0, double z = 0) : x(x), y(y), z(z) {}
    Vec3 operator+(const Vec3& o) const { return {x + o.x, y + o.y, z + o.z}; }
    Vec3 operator-(const Vec3& o) const { return {x - o.x, y - o.y, z - o.z}; }
    Vec3 operator*(double s) const { return {x * s, y * s, z * s}; }
    double norm() const { return std::sqrt(x*x + y*y + z*z); }
};

struct CellState {
    int drone_id;
    Vec3 position;
    double activator = 0.0;
    double inhibitor = 0.0;
    std::string fate = "undifferentiated";
};

class ReactionDiffusion {
    size_t n_;
    double Da_, Di_, f_, k_;

public:
    std::vector<double> activator;
    std::vector<double> inhibitor;

    ReactionDiffusion(size_t n, double Da = 0.1, double Di = 0.4,
                      double f = 0.055, double k = 0.062)
        : n_(n), Da_(Da), Di_(Di), f_(f), k_(k),
          activator(n), inhibitor(n) {
        // Simple seeded initialization
        for (size_t i = 0; i < n; ++i) {
            activator[i] = 0.5 + 0.1 * std::sin(static_cast<double>(i));
            inhibitor[i] = 0.5 + 0.1 * std::cos(static_cast<double>(i));
        }
    }

    void step(double dt = 0.1) {
        std::vector<double> new_a(n_), new_b(n_);
        for (size_t i = 0; i < n_; ++i) {
            size_t left = (i + n_ - 1) % n_;
            size_t right = (i + 1) % n_;
            double lap_a = activator[left] + activator[right] - 2 * activator[i];
            double lap_b = inhibitor[left] + inhibitor[right] - 2 * inhibitor[i];
            double reaction = activator[i] * activator[i] * inhibitor[i];
            double da = Da_ * lap_a - reaction + f_ * (1 - activator[i]);
            double db = Di_ * lap_b + reaction - (f_ + k_) * inhibitor[i];
            new_a[i] = std::clamp(activator[i] + da * dt, 0.0, 1.0);
            new_b[i] = std::clamp(inhibitor[i] + db * dt, 0.0, 1.0);
        }
        activator = std::move(new_a);
        inhibitor = std::move(new_b);
    }

    void run(int steps, double dt = 0.1) {
        for (int s = 0; s < steps; ++s) step(dt);
    }
};

class MorphogenesisEngine {
    size_t n_drones_;
    ReactionDiffusion rd_;
    Formation target_;
    double time_ = 0;

public:
    std::vector<CellState> cells;

    MorphogenesisEngine(size_t n_drones)
        : n_drones_(n_drones), rd_(n_drones), target_(Formation::Circle) {
        cells.reserve(n_drones);
        for (size_t i = 0; i < n_drones; ++i) {
            CellState cell;
            cell.drone_id = static_cast<int>(i);
            cell.position = Vec3(
                50.0 * std::cos(2.0 * M_PI * i / n_drones),
                50.0 * std::sin(2.0 * M_PI * i / n_drones),
                30.0
            );
            cells.push_back(cell);
        }
    }

    std::vector<Vec3> target_positions(Formation f) const {
        std::vector<Vec3> targets;
        size_t n = n_drones_;
        switch (f) {
        case Formation::Circle:
            for (size_t i = 0; i < n; ++i) {
                double angle = 2.0 * M_PI * i / n;
                targets.push_back({30 * std::cos(angle), 30 * std::sin(angle), 30});
            }
            break;
        case Formation::Line:
            for (size_t i = 0; i < n; ++i)
                targets.push_back({static_cast<double>(i) * 5.0 - n * 2.5, 0, 30});
            break;
        case Formation::VShape:
            for (size_t i = 0; i < n; ++i) {
                int side = (i % 2 == 0) ? 1 : -1;
                int idx = static_cast<int>(i / 2);
                targets.push_back({idx * 5.0, side * idx * 3.0, 30});
            }
            break;
        case Formation::Grid: {
            int cols = static_cast<int>(std::ceil(std::sqrt(n)));
            for (size_t i = 0; i < n; ++i)
                targets.push_back({(i % cols) * 8.0, (i / cols) * 8.0, 30});
            break;
        }
        case Formation::Spiral:
            for (size_t i = 0; i < n; ++i) {
                double t = i * 0.5;
                targets.push_back({t * 3 * std::cos(t), t * 3 * std::sin(t), 30});
            }
            break;
        case Formation::Ring:
            for (size_t i = 0; i < n; ++i) {
                double angle = 2.0 * M_PI * i / n;
                double r = 20 + 10 * std::sin(3 * angle);
                targets.push_back({r * std::cos(angle), r * std::sin(angle), 30});
            }
            break;
        }
        return targets;
    }

    void assign_roles() {
        for (size_t i = 0; i < cells.size(); ++i) {
            cells[i].activator = rd_.activator[i];
            cells[i].inhibitor = rd_.inhibitor[i];
            if (rd_.activator[i] > 0.6) cells[i].fate = "leader";
            else if (rd_.inhibitor[i] > 0.5) cells[i].fate = "scout";
            else cells[i].fate = "follower";
        }
    }

    double step(double dt = 0.1) {
        time_ += dt;
        rd_.step(dt);
        assign_roles();
        auto targets = target_positions(target_);
        double total_error = 0;
        for (size_t i = 0; i < cells.size() && i < targets.size(); ++i) {
            Vec3 error = targets[i] - cells[i].position;
            double gain = (cells[i].fate == "leader") ? 0.5 : 0.3;
            cells[i].position = cells[i].position + error * (gain * dt);
            total_error += error.norm();
        }
        return total_error / n_drones_;
    }

    double morph_to(Formation f, int steps = 100, double dt = 0.1) {
        target_ = f;
        double final_error = 0;
        for (int s = 0; s < steps; ++s)
            final_error = step(dt);
        return final_error;
    }

    double formation_quality() const {
        auto targets = target_positions(target_);
        double total_error = 0;
        for (size_t i = 0; i < cells.size() && i < targets.size(); ++i)
            total_error += (targets[i] - cells[i].position).norm();
        double avg = total_error / n_drones_;
        return std::max(0.0, 1.0 - avg / 50.0);
    }

    size_t count_role(const std::string& role) const {
        return std::count_if(cells.begin(), cells.end(),
            [&](const CellState& c) { return c.fate == role; });
    }
};

} // namespace morphogenesis
