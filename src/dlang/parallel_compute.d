// P598: ParallelCompute - D language parallel drone state computation
// Phase 598: SIMD-friendly parallel physics for large drone swarms

module sdacs.parallel_compute;

import std.math;
import std.algorithm;
import std.array;
import std.parallelism;
import std.range;

/// Drone state for parallel computation
struct DroneState {
    uint   id;
    float  x, y, z;
    float  vx, vy, vz;
    float  battery;
    ubyte  status;
    float  ax, ay, az;  // acceleration (for next tick)
}

/// Compute 3D distance between two DroneState positions
float distance3d(ref DroneState a, ref DroneState b) @safe @nogc {
    float dx = b.x - a.x;
    float dy = b.y - a.y;
    float dz = b.z - a.z;
    return sqrt(dx*dx + dy*dy + dz*dz);
}

/// Simple APF repulsion force
float[3] apfRepulsion(ref DroneState from, ref DroneState to,
                      float k_rep = 500.0f, float rho_0 = 50.0f) @safe @nogc {
    float dist = distance3d(from, to);
    if (dist >= rho_0 || dist < 0.001f) return [0.0f, 0.0f, 0.0f];
    float mag = k_rep * (1.0f/dist - 1.0f/rho_0) / (dist * dist);
    return [
        mag * (from.x - to.x) / dist,
        mag * (from.y - to.y) / dist,
        mag * (from.z - to.z) / dist
    ];
}

/// Parallel force computation over all drone pairs
void computeAllForces(DroneState[] drones, float dt = 0.1f) {
    immutable n = drones.length;

    // Parallel outer loop over drones
    foreach (i, ref d; parallel(drones)) {
        float fx = 0.0f, fy = 0.0f, fz = 0.0f;
        foreach (j; 0 .. n) {
            if (i == j) continue;
            auto rep = apfRepulsion(d, drones[j]);
            fx += rep[0]; fy += rep[1]; fz += rep[2];
        }
        d.ax = fx; d.ay = fy; d.az = fz;
    }
}

/// Integrate drone positions using Euler method
void integratePositions(DroneState[] drones, float dt = 0.1f) @safe {
    foreach (ref d; parallel(drones)) {
        d.vx += d.ax * dt;
        d.vy += d.ay * dt;
        d.vz += d.az * dt;
        d.x  += d.vx * dt;
        d.y  += d.vy * dt;
        d.z  += d.vz * dt;
        // Clamp altitude
        if (d.z < 30.0f) d.z = 30.0f;
        if (d.z > 150.0f) d.z = 150.0f;
        // Drain battery
        float speed = sqrt(d.vx*d.vx + d.vy*d.vy + d.vz*d.vz);
        d.battery -= (0.001f + 0.0005f * speed) * dt;
        if (d.battery < 0.0f) d.battery = 0.0f;
    }
}

/// Step the entire swarm simulation
void stepSwarm(DroneState[] drones, float dt = 0.1f) {
    computeAllForces(drones, dt);
    integratePositions(drones, dt);
}

/// Count collision pairs (distance < min_sep)
int countCollisions(DroneState[] drones, float min_sep = 5.0f) @safe {
    int count = 0;
    immutable n = drones.length;
    foreach (i; 0 .. n)
        foreach (j; i+1 .. n)
            if (distance3d(drones[i], drones[j]) < min_sep)
                ++count;
    return count;
}
