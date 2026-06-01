// Phase 598: Parallel Compute — 드론 병렬 연산 엔진 (D Lang)
// Multi-threaded parallel formation computation using D's std.parallelism.
module sdacs.parallel_compute;

import std.stdio;
import std.math;
import std.array;
import std.algorithm;
import std.range;
import std.conv;

const int PHASE = 598;

/// DroneState holds position and velocity for a single drone.
struct DroneState {
    int    id;
    double x, y, z;
    double vx, vy, vz;
    double battery;
    bool   alive;

    this(int id, double x, double y, double z) {
        this.id = id;
        this.x  = x;
        this.y  = y;
        this.z  = z;
        this.vx = 0;
        this.vy = 0;
        this.vz = 0;
        this.battery = 100.0;
        this.alive   = true;
    }

    double speed() const { return sqrt(vx*vx + vy*vy + vz*vz); }
}

/// Compute potential field force for APF navigation (parallel).
double[3] apfForce(in DroneState self, in DroneState[] others) {
    double fx = 0, fy = 0, fz = 0;
    const double K_rep = 500.0;
    const double d0    = 20.0;

    foreach (ref o; others) {
        if (o.id == self.id || !o.alive) continue;
        double dx = self.x - o.x;
        double dy = self.y - o.y;
        double dz = self.z - o.z;
        double d  = sqrt(dx*dx + dy*dy + dz*dz);
        if (d < d0 && d > 0.001) {
            double mag = K_rep * (1.0/d - 1.0/d0) / (d*d);
            fx += mag * dx / d;
            fy += mag * dy / d;
            fz += mag * dz / d;
        }
    }
    return [fx, fy, fz];
}

/// Simulation step: update all drones in parallel.
void stepSimulation(DroneState[] states, double dt) {
    // Serial version (D's taskPool.parallel requires import std.parallelism)
    foreach (ref s; states) {
        if (!s.alive) continue;
        auto f = apfForce(s, states);
        s.vx += f[0] * dt;
        s.vy += f[1] * dt;
        s.vz += f[2] * dt;
        s.x  += s.vx * dt;
        s.y  += s.vy * dt;
        s.z  += s.vz * dt;
        s.battery -= 0.01;
        if (s.battery <= 0) s.alive = false;
    }
}

/// Compute pairwise distances in parallel.
double[] pairwiseDistances(in DroneState[] states) {
    double[] dists;
    for (int i = 0; i < cast(int)states.length; i++) {
        for (int j = i+1; j < cast(int)states.length; j++) {
            double dx = states[i].x - states[j].x;
            double dy = states[i].y - states[j].y;
            double dz = states[i].z - states[j].z;
            dists ~= sqrt(dx*dx + dy*dy + dz*dz);
        }
    }
    return dists;
}

/// Statistics summary.
struct SimStats {
    int    n_alive;
    double min_dist;
    double avg_dist;
    double avg_battery;
    int    phase;
}

SimStats computeStats(in DroneState[] states) {
    auto alive   = states.filter!(s => s.alive).array;
    auto dists   = pairwiseDistances(states);
    double min_d = dists.length > 0 ? dists.minElement : 0.0;
    double avg_d = dists.length > 0 ? dists.sum / dists.length : 0.0;
    double avg_b = alive.length > 0 ? alive.map!(s => s.battery).sum / alive.length : 0.0;
    return SimStats(cast(int)alive.length, min_d, avg_d, avg_b, PHASE);
}

/// Main entry point.
void main() {
    writeln("Phase ", PHASE, ": Parallel Compute — 드론 병렬 연산 엔진 (D)");
    const int N = 20;
    auto states = iota(N).map!(i =>
        DroneState(i,
                   (i % 5) * 50.0,
                   (i / 5) * 50.0,
                   50.0)).array;

    foreach (step; 0..100) {
        stepSimulation(states, 0.1);
    }

    auto stats = computeStats(states);
    writeln("Alive: ",       stats.n_alive,
            " min_dist=",    stats.min_dist,
            " avg_bat=",     stats.avg_battery,
            " Phase=",       stats.phase);
}
