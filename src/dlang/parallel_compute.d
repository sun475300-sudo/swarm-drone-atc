// Phase 598 — D language parallel compute with DroneState struct
// SDACS parallel drone state propagation using D's std.parallelism

import std.stdio;
import std.math;
import std.algorithm;
import std.array;
import std.parallelism;
import std.random;
import std.range;

// ---- DroneState ----

struct DroneState {
    int    id;
    double lat;
    double lon;
    double altM;
    double vx;
    double vy;
    double vz;
    double battPct;
    double speedMps;
    bool   active;

    // Compute speed magnitude from velocity components
    double speed() const pure nothrow {
        return sqrt(vx*vx + vy*vy + vz*vz);
    }

    // Apply a simple Euler integration step to the DroneState position
    DroneState step(double dtSec) const pure nothrow {
        enum EARTH_R = 6_371_000.0;
        enum RAD_DEG = PI / 180.0;
        DroneState next = this;
        next.lat   = lat + (vy / EARTH_R) * (1.0 / RAD_DEG) * dtSec;
        next.lon   = lon + (vx / (EARTH_R * cos(lat * RAD_DEG))) * (1.0 / RAD_DEG) * dtSec;
        next.altM  = altM + vz * dtSec;
        next.speedMps = next.speed();
        return next;
    }

    // Check if the DroneState is within safe flight envelope
    bool isSafe() const pure nothrow {
        return altM >= 0.0 && altM <= 400.0
            && speedMps <= 30.0
            && battPct >= 10.0;
    }

    string toString() const {
        import std.format : format;
        return format!"DroneState[%d] lat=%.5f lon=%.5f alt=%.1fm spd=%.1f bat=%.0f%% safe=%s"(
            id, lat, lon, altM, speedMps, battPct, isSafe());
    }
}

// ---- Conflict detection between two DroneState instances ----

double haversineM(double lat1, double lon1, double lat2, double lon2) pure nothrow {
    enum R = 6_371_000.0;
    auto dlat = (lat2 - lat1) * PI / 180.0;
    auto dlon = (lon2 - lon1) * PI / 180.0;
    auto a = sin(dlat/2)^^2 + cos(lat1*PI/180.0)*cos(lat2*PI/180.0)*sin(dlon/2)^^2;
    return R * 2 * atan2(sqrt(a), sqrt(1-a));
}

bool conflictDetected(in DroneState a, in DroneState b, double sepM = 10.0) pure nothrow {
    auto groundDist = haversineM(a.lat, a.lon, b.lat, b.lon);
    auto altDiff = abs(a.altM - b.altM);
    return groundDist < sepM && altDiff < sepM;
}

// ---- Parallel simulation step ----

DroneState[] parallelStep(DroneState[] states, double dtSec) {
    auto results = new DroneState[states.length];
    foreach (i, ref s; parallel(states)) {
        results[i] = s.step(dtSec);
    }
    return results;
}

// ---- Parallel conflict scan ----

struct ConflictPair {
    int idA, idB;
    double distM;
}

ConflictPair[] parallelConflictScan(DroneState[] states, double sepM = 10.0) {
    import std.concurrency : thisTid;
    ConflictPair[] conflicts;
    auto n = states.length;
    foreach (i; iota(n)) {
        foreach (j; iota(i + 1, n)) {
            auto d = haversineM(states[i].lat, states[i].lon, states[j].lat, states[j].lon);
            if (d < sepM) {
                conflicts ~= ConflictPair(states[i].id, states[j].id, d);
            }
        }
    }
    return conflicts;
}

// ---- Entry point ----

void main() {
    auto rng = Random(42);

    // Initialise a fleet of DroneState instances
    const nDrones = 8;
    DroneState[] fleet = iota(nDrones).map!(i => DroneState(
        id:       i,
        lat:      37.42 + uniform(-0.001, 0.001, rng),
        lon:      127.13 + uniform(-0.001, 0.001, rng),
        altM:     50.0 + uniform(0.0, 50.0, rng),
        vx:       uniform(-5.0, 5.0, rng),
        vy:       uniform(-5.0, 5.0, rng),
        vz:       0.0,
        battPct:  80.0 + uniform(0.0, 20.0, rng),
        speedMps: 0.0,
        active:   true
    )).array;

    // Fix up speedMps after construction
    foreach (ref d; fleet) d.speedMps = d.speed();

    writeln("=== Initial DroneState fleet ===");
    foreach (d; fleet) writeln(d);

    // Run 5 parallel simulation steps
    foreach (step; 0..5) {
        fleet = parallelStep(fleet, 0.1);
    }

    writeln("\n=== After 5 steps ===");
    foreach (d; fleet) writeln(d);

    auto conflicts = parallelConflictScan(fleet, 50.0);
    writefln("\nConflicts detected: %d", conflicts.length);
    foreach (c; conflicts) {
        writefln("  DroneState %d <-> DroneState %d  dist=%.1fm", c.idA, c.idB, c.distM);
    }
}
