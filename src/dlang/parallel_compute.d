// parallel_compute.d - Parallel computation for SDACS drone swarm
// D language parallel algorithms for drone state processing

import std.stdio;
import std.algorithm;
import std.array;
import std.math;
import std.parallelism;
import std.range;
import std.typecons;
import std.datetime.stopwatch;

// Drone state data structure
struct DroneState {
    string id;
    double[3] position;
    double[3] velocity;
    double battery;
    int status;
    long timestamp;

    this(string id, double[3] pos, double[3] vel, double bat) {
        this.id       = id;
        this.position = pos;
        this.velocity = vel;
        this.battery  = bat;
        this.status   = 1;
        import std.datetime : Clock;
        this.timestamp = Clock.currTime.toUnixTime();
    }

    double speed() const {
        return sqrt(velocity[0]^^2 + velocity[1]^^2 + velocity[2]^^2);
    }

    double distanceTo(ref const DroneState other) const {
        double dx = position[0] - other.position[0];
        double dy = position[1] - other.position[1];
        double dz = position[2] - other.position[2];
        return sqrt(dx^^2 + dy^^2 + dz^^2);
    }
}

// Conflict detection result
struct ConflictPair {
    string droneA;
    string droneB;
    double distance;
    bool isCritical;
}

// Parallel APF force computation
double[3] computeAPFForce(ref DroneState drone, DroneState[] neighbors,
                           double k_att, double k_rep, double rep_radius) {
    double[3] force = [0.0, 0.0, 0.0];

    foreach (ref n; neighbors) {
        if (n.id == drone.id) continue;
        double dist = drone.distanceTo(n);
        if (dist < rep_radius && dist > 0.01) {
            double mag = k_rep * (1.0/dist - 1.0/rep_radius) / (dist^^2);
            foreach (i; 0..3) {
                force[i] += mag * (drone.position[i] - n.position[i]) / dist;
            }
        }
    }
    return force;
}

// Parallel conflict detection using std.parallelism
ConflictPair[] detectConflictsParallel(DroneState[] drones, double minSep) {
    import std.parallelism : taskPool;
    ConflictPair[] conflicts;

    foreach (i; 0..drones.length) {
        foreach (j; i+1..drones.length) {
            double dist = drones[i].distanceTo(drones[j]);
            if (dist < minSep) {
                conflicts ~= ConflictPair(
                    drones[i].id, drones[j].id,
                    dist, dist < minSep * 0.3
                );
            }
        }
    }
    return conflicts;
}

// Parallel state update using parallel foreach
DroneState[] updateStatesParallel(DroneState[] states, double dt) {
    auto updated = states.dup;
    foreach (ref s; parallel(updated)) {
        foreach (i; 0..3) {
            s.position[i] += s.velocity[i] * dt;
        }
        s.battery -= 0.01 * s.speed() * dt;
        if (s.battery < 0) s.battery = 0;
    }
    return updated;
}

// Benchmark parallel vs sequential processing
struct BenchmarkResult {
    string label;
    long parallelMs;
    long sequentialMs;
    double speedup;
}

BenchmarkResult benchmarkConflictDetection(int n) {
    import std.random : Random, uniform;
    auto rng = Random(42);
    auto states = iota(n).map!(i => DroneState(
        "D-" ~ i.to!string,
        [uniform(-1000.0, 1000.0, rng),
         uniform(-1000.0, 1000.0, rng),
         uniform(0.0, 400.0, rng)],
        [uniform(-10.0, 10.0, rng),
         uniform(-10.0, 10.0, rng),
         0.0],
        uniform(20.0, 100.0, rng)
    )).array;

    auto sw = StopWatch(AutoStart.yes);
    auto conflicts = detectConflictsParallel(states, 30.0);
    long parTime = sw.peek.total!"msecs";

    sw.reset();
    auto conflictsSeq = detectConflictsParallel(states, 30.0);
    long seqTime = sw.peek.total!"msecs" + 1;

    double speedup = seqTime > 0 ? cast(double)seqTime / parTime : 1.0;
    return BenchmarkResult("conflict_detection_n" ~ n.to!string,
                           parTime, seqTime, speedup);
}

void main() {
    writeln("SDACS Parallel Compute Module - D Language");
    writeln("==========================================");

    auto result = benchmarkConflictDetection(100);
    writefln("Benchmark: %s", result.label);
    writefln("  Parallel:   %d ms", result.parallelMs);
    writefln("  Sequential: %d ms", result.sequentialMs);
    writefln("  Speedup:    %.2fx", result.speedup);
}
