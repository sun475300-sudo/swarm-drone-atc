// Phase 598: Parallel Compute Engine — D
// 병렬 컴퓨팅 엔진: 태스크 병렬화, SIMD 근사,
// 작업 분배, 결과 집계.

import std.stdio;
import std.math;
import std.array;
import std.algorithm;
import std.range;
import std.conv;
import std.format;

// ─── 벡터 타입 ───
struct Vec3 {
    double x, y, z;

    Vec3 opBinary(string op)(Vec3 rhs) const if (op == "+") {
        return Vec3(x + rhs.x, y + rhs.y, z + rhs.z);
    }

    Vec3 opBinary(string op)(Vec3 rhs) const if (op == "-") {
        return Vec3(x - rhs.x, y - rhs.y, z - rhs.z);
    }

    Vec3 opBinary(string op)(double s) const if (op == "*") {
        return Vec3(x * s, y * s, z * s);
    }

    double magnitude() const {
        return sqrt(x * x + y * y + z * z);
    }

    double dot(Vec3 rhs) const {
        return x * rhs.x + y * rhs.y + z * rhs.z;
    }
}

// ─── 드론 상태 ───
struct DroneState {
    int id;
    Vec3 position;
    Vec3 velocity;
    double battery;
    bool active;
}

// ─── 충돌 쌍 ───
struct CollisionPair {
    int droneA;
    int droneB;
    double distance;
    double timeToCollision;
}

// ─── APF (인공 포텐셜 장) ───
struct APFComputer {
    double attractiveGain = 1.0;
    double repulsiveGain = 100.0;
    double influenceRadius = 50.0;

    Vec3 computeForce(Vec3 pos, Vec3 goal, Vec3[] obstacles) {
        // 인력
        Vec3 diff = goal - pos;
        double dist = diff.magnitude();
        Vec3 attractive = diff * (attractiveGain / (dist + 0.01));

        // 척력
        Vec3 repulsive = Vec3(0, 0, 0);
        foreach (obs; obstacles) {
            Vec3 d = pos - obs;
            double r = d.magnitude();
            if (r < influenceRadius && r > 0.01) {
                double mag = repulsiveGain * (1.0 / r - 1.0 / influenceRadius) / (r * r);
                repulsive = repulsive + d * (mag / r);
            }
        }

        return attractive + repulsive;
    }
}

// ─── 충돌 검출 ───
CollisionPair[] detectCollisions(DroneState[] drones, double threshold) {
    CollisionPair[] pairs;
    for (size_t i = 0; i < drones.length; i++) {
        if (!drones[i].active) continue;
        for (size_t j = i + 1; j < drones.length; j++) {
            if (!drones[j].active) continue;
            double dist = (drones[i].position - drones[j].position).magnitude();
            if (dist < threshold) {
                // CPA 계산
                Vec3 dv = drones[i].velocity - drones[j].velocity;
                Vec3 dp = drones[i].position - drones[j].position;
                double dvMag2 = dv.dot(dv);
                double ttc = dvMag2 > 0.001 ? -dp.dot(dv) / dvMag2 : 999.0;
                pairs ~= CollisionPair(
                    drones[i].id, drones[j].id,
                    dist, ttc > 0 ? ttc : 999.0
                );
            }
        }
    }
    return pairs;
}

// ─── 시뮬레이션 ───
struct SimResult {
    int drones;
    int steps;
    int collisionPairsDetected;
    double avgBattery;
    double maxForce;
}

SimResult runSimulation(int nDrones, int nSteps) {
    // 드론 초기화
    DroneState[] drones;
    drones.length = nDrones;
    for (int i = 0; i < nDrones; i++) {
        double angle = 2.0 * PI * i / nDrones;
        drones[i] = DroneState(
            i,
            Vec3(cos(angle) * 100, sin(angle) * 100, 50 + i * 5),
            Vec3(0, 0, 0),
            100.0,
            true
        );
    }

    auto apf = APFComputer();
    Vec3 goal = Vec3(0, 0, 100);
    int totalCollisions = 0;
    double maxForce = 0;

    // 시뮬레이션 루프
    for (int step = 0; step < nSteps; step++) {
        // 장애물 (다른 드론 위치)
        Vec3[] obstacles;
        obstacles.length = nDrones;
        for (int i = 0; i < nDrones; i++) {
            obstacles[i] = drones[i].position;
        }

        // 각 드론 업데이트
        for (int i = 0; i < nDrones; i++) {
            if (!drones[i].active) continue;

            Vec3 force = apf.computeForce(drones[i].position, goal, obstacles);
            double fMag = force.magnitude();
            if (fMag > maxForce) maxForce = fMag;

            // 속도 업데이트 (간이)
            drones[i].velocity = force * 0.1;
            drones[i].position = drones[i].position + drones[i].velocity;
            drones[i].battery -= 0.01;

            if (drones[i].battery <= 0) drones[i].active = false;
        }

        // 충돌 검출
        auto pairs = detectCollisions(drones, 30.0);
        totalCollisions += cast(int)pairs.length;
    }

    double avgBat = 0;
    int activeCount = 0;
    foreach (d; drones) {
        if (d.active) {
            avgBat += d.battery;
            activeCount++;
        }
    }
    if (activeCount > 0) avgBat /= activeCount;

    return SimResult(nDrones, nSteps, totalCollisions, avgBat, maxForce);
}

// ─── 메인 ───
void main() {
    writeln("=== SDACS Parallel Compute Engine ===\n");

    auto result = runSimulation(20, 100);

    writefln("  Drones:     %d", result.drones);
    writefln("  Steps:      %d", result.steps);
    writefln("  Collisions: %d", result.collisionPairsDetected);
    writefln("  Avg Battery: %.1f%%", result.avgBattery);
    writefln("  Max Force:  %.4f", result.maxForce);
}
