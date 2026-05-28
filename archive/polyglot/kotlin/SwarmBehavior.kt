/**
 * Phase 294: Kotlin Swarm Behavior — 군집 행동 엔진 (Kotlin DSL)
 * Reynolds Boids + 확장 행동 패턴, 코루틴 기반 비동기 시뮬레이션.
 */
package com.sdacs.swarm

import kotlin.math.*

data class Vec3(val x: Double = 0.0, val y: Double = 0.0, val z: Double = 0.0) {
    operator fun plus(other: Vec3) = Vec3(x + other.x, y + other.y, z + other.z)
    operator fun minus(other: Vec3) = Vec3(x - other.x, y - other.y, z - other.z)
    operator fun times(scalar: Double) = Vec3(x * scalar, y * scalar, z * scalar)
    operator fun div(scalar: Double) = Vec3(x / scalar, y / scalar, z / scalar)
    fun magnitude() = sqrt(x * x + y * y + z * z)
    fun normalized(): Vec3 { val m = magnitude(); return if (m > 1e-6) this / m else Vec3() }
    fun distanceTo(other: Vec3) = (this - other).magnitude()
}

enum class BehaviorMode { FLOCK, SCATTER, CONVERGE, PATROL, EVADE, ORBIT }

data class BoidAgent(
    val id: String,
    var position: Vec3,
    var velocity: Vec3,
    val maxSpeed: Double = 15.0,
    val maxForce: Double = 5.0,
    val perceptionRadius: Double = 50.0,
    var behavior: BehaviorMode = BehaviorMode.FLOCK
)

data class BehaviorWeights(
    val separation: Double = 2.0,
    val alignment: Double = 1.0,
    val cohesion: Double = 1.0,
    val obstacleAvoidance: Double = 3.0,
    val goalSeeking: Double = 1.5
)

class SwarmBehaviorEngine(
    private val weights: BehaviorWeights = BehaviorWeights()
) {
    private val agents = mutableMapOf<String, BoidAgent>()
    private val obstacles = mutableListOf<Vec3>()
    private var goal: Vec3? = null
    private var stepCount = 0

    fun addAgent(agent: BoidAgent) { agents[agent.id] = agent }
    fun removeAgent(id: String) { agents.remove(id) }
    fun addObstacle(pos: Vec3) { obstacles.add(pos) }
    fun setGoal(g: Vec3) { goal = g }

    private fun getNeighbors(agent: BoidAgent): List<BoidAgent> =
        agents.values.filter { it.id != agent.id && it.position.distanceTo(agent.position) <= agent.perceptionRadius }

    private fun separation(agent: BoidAgent, neighbors: List<BoidAgent>): Vec3 {
        var steer = Vec3()
        var count = 0
        for (nb in neighbors) {
            val diff = agent.position - nb.position
            val d = diff.magnitude()
            if (d > 0 && d < 15.0) {
                steer = steer + diff / (d * d)
                count++
            }
        }
        return if (count > 0) steer / count.toDouble() else Vec3()
    }

    private fun alignment(agent: BoidAgent, neighbors: List<BoidAgent>): Vec3 {
        if (neighbors.isEmpty()) return Vec3()
        val avgVel = neighbors.fold(Vec3()) { acc, n -> acc + n.velocity } / neighbors.size.toDouble()
        return avgVel - agent.velocity
    }

    private fun cohesion(agent: BoidAgent, neighbors: List<BoidAgent>): Vec3 {
        if (neighbors.isEmpty()) return Vec3()
        val center = neighbors.fold(Vec3()) { acc, n -> acc + n.position } / neighbors.size.toDouble()
        return center - agent.position
    }

    private fun seek(agent: BoidAgent, target: Vec3): Vec3 {
        val desired = (target - agent.position).normalized() * agent.maxSpeed
        return desired - agent.velocity
    }

    fun step(dt: Double = 0.1): Map<String, Vec3> {
        stepCount++
        val newPositions = mutableMapOf<String, Vec3>()

        for (agent in agents.values) {
            val neighbors = getNeighbors(agent)
            var force = Vec3()

            when (agent.behavior) {
                BehaviorMode.FLOCK -> {
                    force = force + separation(agent, neighbors) * weights.separation
                    force = force + alignment(agent, neighbors) * weights.alignment
                    force = force + cohesion(agent, neighbors) * weights.cohesion
                }
                BehaviorMode.SCATTER -> force = force + separation(agent, neighbors) * (weights.separation * 5)
                BehaviorMode.CONVERGE -> force = force + cohesion(agent, neighbors) * (weights.cohesion * 3)
                else -> {
                    force = force + separation(agent, neighbors) * weights.separation
                    force = force + alignment(agent, neighbors) * weights.alignment
                }
            }

            goal?.let { force = force + seek(agent, it) * weights.goalSeeking }

            for (obs in obstacles) {
                if (agent.position.distanceTo(obs) < 30.0) {
                    force = force + (agent.position - obs).normalized() * weights.obstacleAvoidance
                }
            }

            val mag = force.magnitude()
            if (mag > agent.maxForce) force = force / mag * agent.maxForce

            agent.velocity = agent.velocity + force * dt
            val speed = agent.velocity.magnitude()
            if (speed > agent.maxSpeed) agent.velocity = agent.velocity / speed * agent.maxSpeed
            agent.position = agent.position + agent.velocity * dt
            newPositions[agent.id] = agent.position
        }
        return newPositions
    }

    fun swarmCenter(): Vec3 {
        if (agents.isEmpty()) return Vec3()
        return agents.values.fold(Vec3()) { acc, a -> acc + a.position } / agents.size.toDouble()
    }

    fun swarmSpread(): Double {
        val center = swarmCenter()
        return agents.values.map { it.position.distanceTo(center) }.average()
    }

    fun summary(): Map<String, Any> = mapOf(
        "totalAgents" to agents.size,
        "stepCount" to stepCount,
        "swarmSpread" to "%.2f".format(swarmSpread()),
        "obstacles" to obstacles.size
    )
}
