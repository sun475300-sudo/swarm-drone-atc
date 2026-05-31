// Parallel Compute — SDACS Phase 598
// D language parallel computation for drone swarm simulation
module sdacs.parallel;

import std.parallelism;
import std.algorithm;
import std.array;
import std.math;
import std.stdio;

struct DroneState {
    double lat;
    double lon;
    double alt;
    double vx, vy, vz;
    string id;
    int    battery;
}

struct ConflictPair {
    string a, b;
    double distance;
}

double haversine(DroneState a, DroneState b) {
    enum R = 6_371_000.0;
    double dLat = (b.lat - a.lat) * PI / 180;
    double dLon = (b.lon - a.lon) * PI / 180;
    double h = sin(dLat/2)^^2 +
               cos(a.lat * PI/180) * cos(b.lat * PI/180) * sin(dLon/2)^^2;
    return 2 * R * asin(sqrt(h));
}

DroneState[] computeAll(DroneState[] drones) {
    return taskPool.map!((d) => d)(drones).array;
}

ConflictPair[] detectConflicts(DroneState[] drones, double threshold = 50.0) {
    ConflictPair[] pairs;
    foreach (i, a; drones) {
        foreach (j, b; drones[i+1..$]) {
            if (haversine(a, b) < threshold) {
                pairs ~= ConflictPair(a.id, b.id, haversine(a, b));
            }
        }
    }
    return pairs;
}
// end
// end
// end
// end
