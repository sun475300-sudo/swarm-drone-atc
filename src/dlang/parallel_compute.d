// Phase 598: parallel_compute — D 언어 기반 병렬 컴퓨팅
// SDACS Parallel Computation for Swarm Drone State Updates

import std.stdio;
import std.algorithm;
import std.array;
import std.math;
import std.parallelism;
import std.range;
import std.conv;
import std.string;
import std.format;

// 드론 상태 구조체 (DroneState)
struct DroneState {
    int      droneId;
    double   lat;
    double   lon;
    double   alt;
    double   vx, vy, vz;  // 속도 (m/s)
    double   battery;
    double   heading;      // 방위각 (도)
    bool     armed;
    string   mode;

    string toString() const {
        return format("D%d(%.3f,%.3f,%.1fm bat=%.1f%%)", droneId, lat, lon, alt, battery);
    }
}

// 3D 유클리드 거리 (위경도 근사)
double separationMeters(ref const DroneState a, ref const DroneState b) pure nothrow {
    immutable double dx = (a.lon - b.lon) * 111320.0 * cos(a.lat * PI / 180.0);
    immutable double dy = (a.lat - b.lat) * 111320.0;
    immutable double dz = a.alt - b.alt;
    return sqrt(dx*dx + dy*dy + dz*dz);
}

// APF (인공 포텐셜 장) 반발력 계산
double[] computeRepulsiveForce(ref const DroneState drone, DroneState[] neighbors, double eta = 100.0, double d0 = 10.0) {
    double fx = 0.0, fy = 0.0, fz = 0.0;
    foreach (ref n; neighbors) {
        if (n.droneId == drone.droneId) continue;
        double dist = separationMeters(drone, n);
        if (dist > 0.0 && dist < d0) {
            double coeff = eta * (1.0/dist - 1.0/d0) / (dist * dist);
            fx += coeff * (drone.lat - n.lat) * 111320.0;
            fy += coeff * (drone.lon - n.lon) * 111320.0 * cos(drone.lat * PI / 180.0);
            fz += coeff * (drone.alt - n.alt);
        }
    }
    return [fx, fy, fz];
}

// 배터리 소모 모델 (단순 선형)
double consumeBattery(double battery, double speed, double dt) pure nothrow {
    immutable double rate = 0.1 + speed * 0.02;  // % per second
    return max(0.0, battery - rate * dt);
}

// 상태 업데이트 (단일 드론, 순수 함수)
DroneState updateDroneState(DroneState state, double dt, double wind_u = 0.0, double wind_v = 0.0) pure nothrow {
    DroneState next = state;
    // 위치 적분
    next.lat = state.lat + (state.vy + wind_v) * dt / 111320.0;
    next.lon = state.lon + (state.vx + wind_u) * dt / (111320.0 * cos(state.lat * PI / 180.0));
    next.alt = state.alt + state.vz * dt;
    next.alt = max(0.0, next.alt);
    // 배터리 소모
    immutable double speed = sqrt(state.vx*state.vx + state.vy*state.vy + state.vz*state.vz);
    next.battery = consumeBattery(state.battery, speed, dt);
    // 배터리 0% → RTL 모드
    if (next.battery <= 0.0) next.mode = "RTL";
    return next;
}

// 병렬 군집 상태 업데이트
DroneState[] parallelSwarmUpdate(DroneState[] swarm, double dt) {
    auto results = new DroneState[swarm.length];
    // std.parallelism.parallel로 병렬 실행
    foreach (i, ref state; parallel(swarm)) {
        results[i] = updateDroneState(state, dt);
    }
    return results;
}

// 충돌 위험 드론 쌍 탐지
struct ConflictPair {
    int droneA, droneB;
    double distance;
}

ConflictPair[] detectConflicts(DroneState[] swarm, double threshold = 5.0) {
    ConflictPair[] conflicts;
    for (int i = 0; i < cast(int)swarm.length; i++) {
        for (int j = i + 1; j < cast(int)swarm.length; j++) {
            double dist = separationMeters(swarm[i], swarm[j]);
            if (dist < threshold) {
                conflicts ~= ConflictPair(swarm[i].droneId, swarm[j].droneId, dist);
            }
        }
    }
    return conflicts;
}

// 군집 분산 지수
double swarmDispersion(DroneState[] swarm) {
    if (swarm.length < 2) return 0.0;
    double cLat = swarm.map!(s => s.lat).sum / swarm.length;
    double cLon = swarm.map!(s => s.lon).sum / swarm.length;
    double cAlt = swarm.map!(s => s.alt).sum / swarm.length;
    double totalDist = 0.0;
    foreach (ref s; swarm) {
        double dx = (s.lon - cLon) * 111320.0 * cos(cLat * PI / 180.0);
        double dy = (s.lat - cLat) * 111320.0;
        double dz = s.alt - cAlt;
        totalDist += sqrt(dx*dx + dy*dy + dz*dz);
    }
    return totalDist / swarm.length;
}

void main() {
    writeln("SDACS Parallel Compute — Phase 598\n");

    // 초기 군집 상태 생성
    immutable int N_DRONES = 8;
    DroneState[] swarm = iota(N_DRONES).map!(i =>
        DroneState(
            droneId: i,
            lat: 37.500 + i * 0.001,
            lon: 127.000 + i * 0.001,
            alt: 50.0 + i * 2.0,
            vx: 3.0 + i % 3,
            vy: 2.0 + i % 2,
            vz: 0.1,
            battery: 95.0 - i * 2.0,
            heading: i * 45.0,
            armed: true,
            mode: "GUIDED"
        )
    ).array;

    writefln("군집 초기화: %d 드론", swarm.length);
    writefln("초기 분산 지수: %.2fm", swarmDispersion(swarm));

    // 병렬 상태 업데이트 (10 스텝)
    writeln("\n병렬 시뮬레이션 (10스텝 × 0.1s):");
    foreach (step; 0..10) {
        swarm = parallelSwarmUpdate(swarm, 0.1);
    }

    writefln("업데이트 후 분산 지수: %.2fm", swarmDispersion(swarm));

    // 충돌 감지
    auto conflicts = detectConflicts(swarm, 30.0);
    writefln("\n충돌 위험 쌍: %d건", conflicts.length);
    foreach (ref c; conflicts) {
        writefln("  D%d ↔ D%d: %.1fm", c.droneA, c.droneB, c.distance);
    }

    // 상태 요약
    writeln("\n최종 드론 상태 (상위 3개):");
    foreach (ref s; swarm[0..min(3, $)]) {
        writeln("  ", s.toString());
    }

    writeln("\n병렬 컴퓨팅 완료.");
}
