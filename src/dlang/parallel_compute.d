// Phase 588: Parallel Compute — D Lang
// SDACS parallel drone state computation using D's std.parallelism

module sdacs.parallel_compute;

import std.parallelism;
import std.algorithm;
import std.array;
import std.math;
import std.stdio;
import std.datetime.stopwatch;

/// 3D vector type
struct Vector3 {
    double x, y, z;

    Vector3 opAdd(Vector3 other) const {
        return Vector3(x + other.x, y + other.y, z + other.z);
    }
    Vector3 opSub(Vector3 other) const {
        return Vector3(x - other.x, y - other.y, z - other.z);
    }
    Vector3 opMul(double s) const {
        return Vector3(x * s, y * s, z * s);
    }
    double norm() const {
        return sqrt(x*x + y*y + z*z);
    }
    Vector3 normalized() const {
        double n = norm();
        if (n < 1e-10) return Vector3(0,0,0);
        return Vector3(x/n, y/n, z/n);
    }
    double dot(Vector3 other) const {
        return x*other.x + y*other.y + z*other.z;
    }
}

/// Drone state for parallel computation
struct DroneState {
    string  id;
    Vector3 position;
    Vector3 velocity;
    double  heading;
    double  battery;
    double  altitude;
    bool    active;

    void integrate(Vector3 accel, double dt) {
        velocity = velocity + accel * dt;
        position = position + velocity * dt;
        altitude  = position.z;
        if (battery > 0) battery -= 0.01 * dt * (1.0 + velocity.norm() * 0.05);
        if (battery < 0) battery = 0;
    }
}

/// Conflict pair
struct ConflictPair {
    string drone_a;
    string drone_b;
    double separation;
}

/// APF repulsion force between two drones
Vector3 repulsion(Vector3 posA, Vector3 posB, double k_rep, double d0) {
    auto diff = posA - posB;
    double dist = diff.norm();
    if (dist < 1e-3 || dist > d0) return Vector3(0, 0, 0);
    double mag = k_rep * (1.0/dist - 1.0/d0) / (dist * dist);
    return diff.normalized() * mag;
}

/// Parallel state integration step
void integrateAll(DroneState[] drones, double dt) {
    auto pool = taskPool();
    foreach (ref drone; pool.parallel(drones)) {
        if (!drone.active) continue;
        // Simple gravity compensation + slight forward motion
        auto accel = Vector3(0.1, 0.0, 0.0);
        drone.integrate(accel, dt);
    }
}

/// Parallel conflict detection
ConflictPair[] detectConflicts(const DroneState[] drones, double min_sep) {
    ConflictPair[] conflicts;
    auto n = drones.length;
    auto pool = taskPool();

    // Parallel outer loop using taskPool.amap
    auto indices = iota(0, cast(int)n).array;
    auto local_conflicts = pool.amap!((int i) {
        ConflictPair[] local;
        for (int j = i + 1; j < cast(int)n; j++) {
            auto diff = drones[i].position - drones[j].position;
            double dist = diff.norm();
            if (dist < min_sep) {
                local ~= ConflictPair(drones[i].id, drones[j].id, dist);
            }
        }
        return local;
    })(indices);

    foreach (c; local_conflicts) conflicts ~= c;
    return conflicts;
}

/// Parallel APF force computation
Vector3[] computeAPFForces(const DroneState[] drones,
                           double k_rep = 100.0, double d0 = 50.0) {
    auto n = drones.length;
    auto forces = new Vector3[n];
    auto pool = taskPool();

    foreach (i, ref force; pool.parallel(forces)) {
        if (!drones[i].active) continue;
        Vector3 total = Vector3(0, 0, 0);
        foreach (j, ref other; drones) {
            if (i == j || !other.active) continue;
            total = total + repulsion(drones[i].position, other.position, k_rep, d0);
        }
        force = total;
    }
    return forces;
}

/// Batch battery status check
size_t countLowBattery(const DroneState[] drones, double threshold = 20.0) {
    return count!(d => d.battery < threshold)(drones);
}

/// Statistics over drone fleet
struct FleetStats {
    double avg_battery;
    double avg_speed;
    double avg_altitude;
    size_t active_count;
    size_t low_battery_count;
}

FleetStats computeStats(const DroneState[] drones) {
    auto active = filter!(d => d.active)(drones).array;
    if (active.length == 0) return FleetStats();

    double sum_bat = 0, sum_spd = 0, sum_alt = 0;
    foreach (d; active) {
        sum_bat += d.battery;
        sum_spd += d.velocity.norm();
        sum_alt += d.altitude;
    }
    size_t n = active.length;
    return FleetStats(
        avg_battery:      sum_bat / n,
        avg_speed:        sum_spd / n,
        avg_altitude:     sum_alt / n,
        active_count:     n,
        low_battery_count: countLowBattery(drones)
    );
}

void main() {
    // Demo: create 10 drones and run parallel simulation
    auto drones = new DroneState[10];
    foreach (i, ref d; drones) {
        import std.format : format;
        d.id       = format("D%03d", i);
        d.position = Vector3(i * 30.0, 0, 60.0);
        d.velocity = Vector3(5.0, 0, 0);
        d.battery  = 80.0 + i * 2.0;
        d.active   = true;
    }

    auto sw = StopWatch(AutoStart.yes);
    foreach (_; 0..100) {
        integrateAll(drones, 0.1);
    }
    sw.stop();

    writefln("Simulated 10 drones x 100 steps in %s ms",
             sw.peek.total!"msecs");

    auto stats = computeStats(drones);
    writefln("Fleet stats: avg_bat=%.1f%% avg_spd=%.2fm/s active=%d",
             stats.avg_battery, stats.avg_speed, stats.active_count);

    auto conflicts = detectConflicts(drones, 30.0);
    writefln("Conflicts detected: %d", conflicts.length);
}
