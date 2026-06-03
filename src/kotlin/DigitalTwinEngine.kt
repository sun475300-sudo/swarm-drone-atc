/**
 * Phase 310: Kotlin Digital Twin Sync Engine
 * Coroutine-ready digital twin management with sealed class hierarchy.
 * Immutable state transitions with data classes.
 */

package sdacs.digitaltwin

import kotlin.math.sqrt
import kotlin.math.abs

// ── Types ──────────────────────────────────────────────────────────
data class Vec3(val x: Double = 0.0, val y: Double = 0.0, val z: Double = 0.0) {
    operator fun plus(o: Vec3) = Vec3(x + o.x, y + o.y, z + o.z)
    operator fun minus(o: Vec3) = Vec3(x - o.x, y - o.y, z - o.z)
    operator fun times(s: Double) = Vec3(x * s, y * s, z * s)
    fun length() = sqrt(x * x + y * y + z * z)
    fun distanceTo(o: Vec3) = (this - o).length()
}

sealed class TwinStatus {
    object Synced : TwinStatus()
    object Lagging : TwinStatus()
    object Predicted : TwinStatus()
    object Disconnected : TwinStatus()

    override fun toString(): String = when (this) {
        is Synced -> "SYNCED"
        is Lagging -> "LAGGING"
        is Predicted -> "PREDICTED"
        is Disconnected -> "DISCONNECTED"
    }
}

data class TwinState(
    val twinId: String,
    val physicalPos: Vec3 = Vec3(),
    val physicalVel: Vec3 = Vec3(),
    val digitalPos: Vec3 = Vec3(),
    val syncTimestamp: Double = 0.0,
    val status: TwinStatus = TwinStatus.Disconnected,
    val divergence: Double = 0.0,
    val lagMs: Double = 0.0,
)

data class SyncEvent(
    val eventId: String,
    val twinId: String,
    val eventType: String,
    val status: TwinStatus,
    val timestamp: Double,
)

// ── Digital Twin Engine ────────────────────────────────────────────
class DigitalTwinEngine(
    private val maxLagMs: Double = 500.0,
    private val maxDivergenceM: Double = 5.0,
) {
    private val twins = mutableMapOf<String, TwinState>()
    private val events = mutableListOf<SyncEvent>()
    private var syncCount = 0
    private var eventCounter = 0

    fun registerTwin(twinId: String): TwinState {
        val state = TwinState(twinId = twinId)
        twins[twinId] = state
        return state
    }

    fun updatePhysical(twinId: String, pos: Vec3, vel: Vec3, timestamp: Double) {
        twins[twinId]?.let {
            twins[twinId] = it.copy(
                physicalPos = pos,
                physicalVel = vel,
                syncTimestamp = timestamp,
            )
        }
    }

    fun predict(twinId: String, dt: Double): Vec3? {
        val twin = twins[twinId] ?: return null
        return twin.physicalPos + twin.physicalVel * dt
    }

    fun sync(twinId: String, currentTime: Double): TwinStatus {
        val twin = twins[twinId] ?: return TwinStatus.Disconnected
        syncCount++

        val lagMs = (currentTime - twin.syncTimestamp) * 1000.0
        val divergence = twin.physicalPos.distanceTo(twin.digitalPos)

        val (newStatus, newDigitalPos) = when {
            lagMs > maxLagMs -> TwinStatus.Disconnected to twin.digitalPos
            divergence > maxDivergenceM -> TwinStatus.Lagging to twin.physicalPos
            lagMs > 100.0 -> {
                val predicted = twin.physicalPos + twin.physicalVel * (lagMs / 1000.0)
                TwinStatus.Predicted to predicted
            }
            else -> TwinStatus.Synced to twin.physicalPos
        }

        twins[twinId] = twin.copy(
            digitalPos = newDigitalPos,
            status = newStatus,
            divergence = divergence,
            lagMs = lagMs,
        )

        eventCounter++
        events.add(SyncEvent(
            eventId = "SYNC-%06d".format(eventCounter),
            twinId = twinId,
            eventType = "state_update",
            status = newStatus,
            timestamp = currentTime,
        ))

        return newStatus
    }

    fun syncAll(currentTime: Double): Map<String, TwinStatus> =
        twins.keys.associateWith { sync(it, currentTime) }

    fun getTwin(twinId: String): TwinState? = twins[twinId]

    fun getDivergentTwins(threshold: Double = 2.0): List<String> =
        twins.filter { it.value.divergence > threshold }.keys.toList()

    fun getEvents(twinId: String? = null, limit: Int = 100): List<SyncEvent> {
        val filtered = if (twinId != null) events.filter { it.twinId == twinId } else events
        return filtered.takeLast(limit)
    }

    fun summary(): Map<String, Any> {
        val statusCounts = twins.values.groupBy { it.status }.mapValues { it.value.size }
        val n = maxOf(twins.size, 1)
        val avgLag = twins.values.sumOf { it.lagMs } / n
        val avgDiv = twins.values.sumOf { it.divergence } / n
        return mapOf(
            "totalTwins" to twins.size,
            "syncCount" to syncCount,
            "avgLagMs" to "%.2f".format(avgLag),
            "avgDivergenceM" to "%.3f".format(avgDiv),
            "statusCounts" to statusCounts.mapKeys { it.key.toString() },
            "totalEvents" to events.size,
        )
    }
}

// ── Main ───────────────────────────────────────────────────────────
fun main() {
    val engine = DigitalTwinEngine()
    engine.registerTwin("drone_1")
    engine.registerTwin("drone_2")

    engine.updatePhysical("drone_1", Vec3(10.0, 20.0, 50.0), Vec3(1.0, 0.0, 0.0), 1.0)
    engine.updatePhysical("drone_2", Vec3(30.0, 40.0, 60.0), Vec3(-1.0, 1.0, 0.0), 1.0)

    val results = engine.syncAll(1.05)
    results.forEach { (id, status) -> println("  $id: $status") }

    println(engine.summary())
}
