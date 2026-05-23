/// Phase 310: C++ HIL Physics Engine
/// High-performance quadcopter physics with SIMD-ready vector ops.
/// Cache-friendly memory layout for multi-vehicle simulation.

#include <cmath>
#include <vector>
#include <array>
#include <string>
#include <unordered_map>
#include <algorithm>
#include <numeric>
#include <cstdio>
#include <cassert>

namespace sdacs {

// ── Vector3 ─────────────────────────────────────────────────────
struct Vec3 {
    double x{0}, y{0}, z{0};

    Vec3() = default;
    Vec3(double x, double y, double z) : x(x), y(y), z(z) {}

    Vec3 operator+(const Vec3& o) const { return {x+o.x, y+o.y, z+o.z}; }
    Vec3 operator-(const Vec3& o) const { return {x-o.x, y-o.y, z-o.z}; }
    Vec3 operator*(double s) const { return {x*s, y*s, z*s}; }
    Vec3& operator+=(const Vec3& o) { x+=o.x; y+=o.y; z+=o.z; return *this; }

    double length() const { return std::sqrt(x*x + y*y + z*z); }
    double dot(const Vec3& o) const { return x*o.x + y*o.y + z*o.z; }

    Vec3 normalize() const {
        double len = length();
        if (len < 1e-12) return {0,0,0};
        return *this * (1.0/len);
    }
};

// ── Vehicle State (SoA-friendly) ────────────────────────────────
struct VehicleState {
    Vec3 position;
    Vec3 velocity;
    Vec3 acceleration;
    Vec3 attitude;      // roll, pitch, yaw (rad)
    Vec3 angular_vel;
    std::array<double, 4> motor_rpms{};
    double battery_v{16.8};
    double mass_kg{2.0};
};

// ── Actuator Command ────────────────────────────────────────────
struct ActuatorCommand {
    std::array<double, 4> motor_speeds{};  // RPM
    std::array<double, 4> servo_angles{};  // degrees
    double timestamp{0};
};

// ── Sensor Reading ──────────────────────────────────────────────
enum class SensorType { IMU, GPS, Barometer, Magnetometer, Lidar };

struct SensorReading {
    SensorType type;
    double timestamp;
    std::vector<double> data;
    double noise_std;
    double latency_ms;
};

// ── Physics Engine ──────────────────────────────────────────────
class PhysicsEngine {
public:
    static constexpr double GRAVITY = 9.81;
    static constexpr double THRUST_COEFF = 1e-5;  // N per RPM²
    static constexpr double ARM_LENGTH = 0.25;     // m
    static constexpr double DRAG_COEFF = 0.1;

    void step(VehicleState& state, const ActuatorCommand& cmd, double dt) {
        // Total thrust from 4 motors
        double total_thrust = 0.0;
        for (int i = 0; i < 4; ++i) {
            total_thrust += THRUST_COEFF * cmd.motor_speeds[i] * cmd.motor_speeds[i];
        }

        // Attitude-based thrust direction
        double cy = std::cos(state.attitude.z), sy = std::sin(state.attitude.z);
        double cp = std::cos(state.attitude.x), sp = std::sin(state.attitude.x);
        double cr = std::cos(state.attitude.y), sr = std::sin(state.attitude.y);

        Vec3 thrust_vec{
            total_thrust * (cy*sp*cr + sy*sr),
            total_thrust * (sy*sp*cr - cy*sr),
            total_thrust * cp*cr
        };

        Vec3 gravity{0, 0, -GRAVITY * state.mass_kg};

        // Quadratic drag
        Vec3 drag{
            -DRAG_COEFF * state.velocity.x * std::abs(state.velocity.x),
            -DRAG_COEFF * state.velocity.y * std::abs(state.velocity.y),
            -DRAG_COEFF * state.velocity.z * std::abs(state.velocity.z)
        };

        Vec3 net_force = thrust_vec + gravity + drag;
        state.acceleration = net_force * (1.0 / state.mass_kg);
        state.velocity += state.acceleration * dt;
        state.position += state.velocity * dt;

        // Simple torque model
        double torque_roll  = (cmd.motor_speeds[1] - cmd.motor_speeds[3]) * ARM_LENGTH * THRUST_COEFF;
        double torque_pitch = (cmd.motor_speeds[0] - cmd.motor_speeds[2]) * ARM_LENGTH * THRUST_COEFF;
        state.angular_vel.x += torque_roll * dt;
        state.angular_vel.y += torque_pitch * dt;
        state.attitude += state.angular_vel * dt;

        for (int i = 0; i < 4; ++i) state.motor_rpms[i] = cmd.motor_speeds[i];
    }
};

// ── HIL Simulator ───────────────────────────────────────────────
class HILSimulator {
    std::unordered_map<std::string, VehicleState> vehicles_;
    PhysicsEngine physics_;
    double clock_{0.0};
    double dt_{0.001};  // 1 kHz
    uint64_t step_count_{0};

public:
    HILSimulator(double dt = 0.001) : dt_(dt) {}

    void addVehicle(const std::string& id, Vec3 initial_pos = {}) {
        VehicleState state;
        state.position = initial_pos;
        vehicles_[id] = state;
    }

    void sendCommand(const std::string& id, const ActuatorCommand& cmd) {
        auto it = vehicles_.find(id);
        if (it != vehicles_.end()) {
            physics_.step(it->second, cmd, dt_);
        }
    }

    void step() {
        clock_ += dt_;
        step_count_++;
    }

    void runFor(double duration_sec) {
        int steps = static_cast<int>(duration_sec / dt_);
        for (int i = 0; i < steps; ++i) {
            step();
        }
    }

    const VehicleState* getState(const std::string& id) const {
        auto it = vehicles_.find(id);
        return it != vehicles_.end() ? &it->second : nullptr;
    }

    double clock() const { return clock_; }
    uint64_t stepCount() const { return step_count_; }
    size_t vehicleCount() const { return vehicles_.size(); }

    void reset() {
        clock_ = 0.0;
        step_count_ = 0;
        vehicles_.clear();
    }

    void printSummary() const {
        printf("HIL Simulator: %zu vehicles | Clock: %.4f s | Steps: %llu | dt: %.4f\n",
               vehicles_.size(), clock_, (unsigned long long)step_count_, dt_);
    }
};

}  // namespace sdacs

// ── Tests & Main ────────────────────────────────────────────────
#ifdef SDACS_HIL_MAIN
int main() {
    using namespace sdacs;

    HILSimulator hil;
    hil.addVehicle("drone_1", {0, 0, 50});
    hil.addVehicle("drone_2", {100, 0, 50});

    // Hover thrust: mg = 4 * THRUST_COEFF * rpm²
    // rpm = sqrt(mg / (4 * THRUST_COEFF))
    double hover_rpm = std::sqrt(2.0 * 9.81 / (4.0 * 1e-5));

    ActuatorCommand hover_cmd;
    hover_cmd.motor_speeds = {hover_rpm, hover_rpm, hover_rpm, hover_rpm};

    for (int i = 0; i < 1000; ++i) {
        hil.sendCommand("drone_1", hover_cmd);
        hil.sendCommand("drone_2", hover_cmd);
        hil.step();
    }

    hil.printSummary();

    auto* s1 = hil.getState("drone_1");
    if (s1) {
        printf("Drone 1 — Pos: (%.2f, %.2f, %.2f) | Alt: %.2f\n",
               s1->position.x, s1->position.y, s1->position.z, s1->position.z);
    }

    // Tests
    assert(hil.vehicleCount() == 2);
    assert(hil.stepCount() == 1000);
    assert(hil.clock() > 0.99);
    printf("All assertions passed.\n");

    return 0;
}
#endif
