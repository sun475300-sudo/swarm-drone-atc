/**
 * SDACS 비행 경로 검증기 — Kotlin DSL
 * =====================================
 * 비행 계획 규제 준수 검증 + NFZ 교차 탐지
 *
 * 기능:
 *   - K-UTM 규제 검증 (고도/속도/구역)
 *   - NFZ (No-Fly Zone) 교차 탐지
 *   - 비행 복도 준수 검증
 *   - Kotlin DSL로 규칙 선언적 정의
 *   - 검증 리포트 생성
 */

package com.sdacs.validator

import kotlin.math.sqrt
import kotlin.math.abs
import kotlin.math.pow

// ── 데이터 클래스 ───────────────────────────────────────

data class Vec3(val x: Double, val y: Double, val z: Double) {
    fun distanceTo(other: Vec3): Double =
        sqrt((x - other.x).pow(2) + (y - other.y).pow(2) + (z - other.z).pow(2))

    fun horizontalDistanceTo(other: Vec3): Double =
        sqrt((x - other.x).pow(2) + (y - other.y).pow(2))

    operator fun minus(other: Vec3) = Vec3(x - other.x, y - other.y, z - other.z)
    operator fun plus(other: Vec3) = Vec3(x + other.x, y + other.y, z + other.z)
}

data class Waypoint(
    val position: Vec3,
    val speed: Double = 10.0,    // m/s
    val holdTime: Double = 0.0   // seconds
)

data class FlightPlan(
    val droneId: String,
    val waypoints: List<Waypoint>,
    val droneType: String = "DELIVERY",
    val maxAltitude: Double = 120.0,
    val estimatedDuration: Double = 0.0  // minutes
)

data class NFZ(
    val id: String,
    val center: Vec3,
    val radius: Double,         // meters
    val minAlt: Double = 0.0,
    val maxAlt: Double = 999.0,
    val active: Boolean = true,
    val reason: String = ""
)

data class Corridor(
    val id: String,
    val start: Vec3,
    val end: Vec3,
    val width: Double = 50.0,   // meters
    val minAlt: Double = 30.0,
    val maxAlt: Double = 120.0
)

// ── 검증 결과 ───────────────────────────────────────────

enum class ViolationType {
    ALTITUDE_TOO_HIGH,
    ALTITUDE_TOO_LOW,
    SPEED_EXCEEDED,
    NFZ_VIOLATION,
    CORRIDOR_DEVIATION,
    SEGMENT_TOO_LONG,
    INSUFFICIENT_BATTERY,
    NIGHTTIME_FLIGHT,
    OVERWEIGHT
}

data class Violation(
    val type: ViolationType,
    val message: String,
    val waypointIndex: Int,
    val severity: Int  // 1-5
)

data class ValidationReport(
    val droneId: String,
    val valid: Boolean,
    val score: Double,       // 0-100
    val violations: List<Violation>,
    val warnings: List<String>,
    val totalDistance: Double,
    val maxAltitude: Double,
    val estimatedEnergy: Double
)

// ── 규칙 DSL ────────────────────────────────────────────

class ValidationRule(
    val name: String,
    val check: (FlightPlan, Int, Waypoint) -> Violation?
)

class RuleBuilder {
    val rules = mutableListOf<ValidationRule>()

    fun rule(name: String, check: (FlightPlan, Int, Waypoint) -> Violation?) {
        rules.add(ValidationRule(name, check))
    }
}

fun validationRules(init: RuleBuilder.() -> Unit): List<ValidationRule> {
    val builder = RuleBuilder()
    builder.init()
    return builder.rules
}

// ── 기본 K-UTM 규칙 ────────────────────────────────────

val K_UTM_RULES = validationRules {
    rule("MAX_ALTITUDE") { plan, idx, wp ->
        if (wp.position.z > plan.maxAltitude)
            Violation(ViolationType.ALTITUDE_TOO_HIGH,
                "고도 ${wp.position.z}m > 최대 ${plan.maxAltitude}m (웨이포인트 $idx)",
                idx, 4)
        else null
    }

    rule("MIN_ALTITUDE") { _, idx, wp ->
        if (wp.position.z < 10.0)
            Violation(ViolationType.ALTITUDE_TOO_LOW,
                "고도 ${wp.position.z}m < 최소 10m (웨이포인트 $idx)",
                idx, 3)
        else null
    }

    rule("MAX_SPEED") { _, idx, wp ->
        if (wp.speed > 25.0)
            Violation(ViolationType.SPEED_EXCEEDED,
                "속도 ${wp.speed}m/s > 최대 25m/s (웨이포인트 $idx)",
                idx, 3)
        else null
    }

    rule("SEGMENT_LENGTH") { plan, idx, wp ->
        if (idx > 0) {
            val prev = plan.waypoints[idx - 1]
            val dist = prev.position.distanceTo(wp.position)
            if (dist > 5000.0)
                Violation(ViolationType.SEGMENT_TOO_LONG,
                    "구간 거리 ${dist}m > 5000m (웨이포인트 ${idx-1}→$idx)",
                    idx, 2)
            else null
        } else null
    }
}

// ── 검증기 구현 ─────────────────────────────────────────

class FlightPathValidator(
    private val nfzList: List<NFZ> = emptyList(),
    private val corridors: List<Corridor> = emptyList(),
    private val rules: List<ValidationRule> = K_UTM_RULES
) {

    /** 비행 계획 전체 검증 */
    fun validate(plan: FlightPlan): ValidationReport {
        val violations = mutableListOf<Violation>()
        val warnings = mutableListOf<String>()
        var totalDistance = 0.0
        var maxAlt = 0.0

        // 1. 규칙 기반 검증
        for ((idx, wp) in plan.waypoints.withIndex()) {
            for (rule in rules) {
                rule.check(plan, idx, wp)?.let { violations.add(it) }
            }

            if (wp.position.z > maxAlt) maxAlt = wp.position.z

            if (idx > 0) {
                totalDistance += plan.waypoints[idx - 1].position.distanceTo(wp.position)
            }
        }

        // 2. NFZ 교차 검증
        violations.addAll(checkNFZViolations(plan))

        // 3. 비행 복도 검증
        violations.addAll(checkCorridorViolations(plan))

        // 4. 에너지 추정
        val estimatedEnergy = estimateEnergy(plan, totalDistance)

        // 5. 경고 생성
        if (totalDistance > 10000) warnings.add("총 비행 거리 ${totalDistance}m — 배터리 주의")
        if (maxAlt > 100) warnings.add("최대 고도 ${maxAlt}m — 유인기 주의")
        if (plan.waypoints.size > 50) warnings.add("웨이포인트 ${plan.waypoints.size}개 — 복잡한 경로")

        // 점수 계산
        val score = calculateScore(violations)

        return ValidationReport(
            droneId = plan.droneId,
            valid = violations.none { it.severity >= 4 },
            score = score,
            violations = violations,
            warnings = warnings,
            totalDistance = totalDistance,
            maxAltitude = maxAlt,
            estimatedEnergy = estimatedEnergy
        )
    }

    /** NFZ 교차 검증 */
    private fun checkNFZViolations(plan: FlightPlan): List<Violation> {
        val violations = mutableListOf<Violation>()
        for ((idx, wp) in plan.waypoints.withIndex()) {
            for (nfz in nfzList) {
                if (!nfz.active) continue
                val hDist = wp.position.horizontalDistanceTo(nfz.center)
                val inAltRange = wp.position.z in nfz.minAlt..nfz.maxAlt
                if (hDist < nfz.radius && inAltRange) {
                    violations.add(Violation(
                        ViolationType.NFZ_VIOLATION,
                        "NFZ '${nfz.id}' 침범 (거리: ${hDist}m < ${nfz.radius}m, 웨이포인트 $idx) — ${nfz.reason}",
                        idx, 5
                    ))
                }
            }
        }
        return violations
    }

    /** 비행 복도 이탈 검증 */
    private fun checkCorridorViolations(plan: FlightPlan): List<Violation> {
        if (corridors.isEmpty()) return emptyList()
        val violations = mutableListOf<Violation>()

        for ((idx, wp) in plan.waypoints.withIndex()) {
            val inAnyCorridor = corridors.any { corridor ->
                val lineDir = corridor.end - corridor.start
                val lineLen = corridor.start.distanceTo(corridor.end)
                if (lineLen < 1e-6) return@any false

                // 점-직선 거리 (수평)
                val t = ((wp.position.x - corridor.start.x) * (lineDir.x) +
                         (wp.position.y - corridor.start.y) * (lineDir.y)) / (lineLen * lineLen)
                val tClamped = t.coerceIn(0.0, 1.0)
                val closest = Vec3(
                    corridor.start.x + tClamped * lineDir.x,
                    corridor.start.y + tClamped * lineDir.y,
                    corridor.start.z + tClamped * lineDir.z
                )
                val dist = wp.position.horizontalDistanceTo(closest)
                val altOk = wp.position.z in corridor.minAlt..corridor.maxAlt

                dist <= corridor.width && altOk
            }

            if (!inAnyCorridor && corridors.isNotEmpty()) {
                violations.add(Violation(
                    ViolationType.CORRIDOR_DEVIATION,
                    "비행 복도 이탈 (웨이포인트 $idx)",
                    idx, 2
                ))
            }
        }

        return violations
    }

    /** 에너지 추정 (Wh) */
    private fun estimateEnergy(plan: FlightPlan, totalDistance: Double): Double {
        val baseConsumption = 0.5 // Wh/m (기본)
        val altFactor = plan.waypoints.maxOfOrNull { it.position.z }?.let { 1.0 + it / 500.0 } ?: 1.0
        return totalDistance * baseConsumption * altFactor
    }

    /** 검증 점수 (0-100) */
    private fun calculateScore(violations: List<Violation>): Double {
        if (violations.isEmpty()) return 100.0
        val penalty = violations.sumOf { it.severity * 5.0 }
        return (100.0 - penalty).coerceIn(0.0, 100.0)
    }
}
