// Android Telemetry Module — Kotlin (Phase 613)
// Android telemetry collection and display module for drone monitoring app.

package swarm.android.telemetry

import kotlin.math.roundToInt

// ===== Data Models =====

data class DronePosition(val lat: Double, val lon: Double, val altitudeM: Double)

data class TelemetrySnapshot(
    val droneId: String,
    val timestamp: Long = System.currentTimeMillis(),
    val position: DronePosition,
    val batteryPercent: Double,
    val speedMs: Double,
    val signalRssi: Double,
    val cpuTemp: Double,
    val isHealthy: Boolean = true
)

data class TelemetryAlert(
    val droneId: String,
    val alertType: String,
    val message: String,
    val severity: Int,  // 1=info 2=warn 3=critical
    val timestamp: Long = System.currentTimeMillis()
)

// ===== Telemetry Buffer =====

class TelemetryBuffer(private val maxSize: Int = 500) {
    private val buffer = ArrayDeque<TelemetrySnapshot>()

    fun add(snapshot: TelemetrySnapshot) {
        if (buffer.size >= maxSize) buffer.removeFirst()
        buffer.addLast(snapshot)
    }

    fun latest(): TelemetrySnapshot? = buffer.lastOrNull()

    fun forDrone(droneId: String): List<TelemetrySnapshot> =
        buffer.filter { it.droneId == droneId }

    fun averageBattery(droneId: String): Double {
        val snaps = forDrone(droneId)
        return if (snaps.isEmpty()) 0.0
        else snaps.map { it.batteryPercent }.average()
    }

    fun size() = buffer.size
}

// ===== Alert Engine =====

class TelemetryAlertEngine(
    private val lowBatteryThreshold: Double = 20.0,
    private val minSignalStrength: Double = -85.0,
    private val maxAltitude: Double = 120.0
) {
    private val alertHistory = mutableListOf<TelemetryAlert>()

    fun evaluate(snapshot: TelemetrySnapshot): List<TelemetryAlert> {
        val alerts = mutableListOf<TelemetryAlert>()

        if (snapshot.batteryPercent < lowBatteryThreshold) {
            alerts += TelemetryAlert(
                snapshot.droneId, "LOW_BATTERY",
                "Battery at ${snapshot.batteryPercent.roundToInt()}%",
                if (snapshot.batteryPercent < 10.0) 3 else 2
            )
        }

        if (snapshot.signalRssi < minSignalStrength) {
            alerts += TelemetryAlert(
                snapshot.droneId, "WEAK_SIGNAL",
                "RSSI: ${snapshot.signalRssi} dBm",
                2
            )
        }

        if (snapshot.position.altitudeM > maxAltitude) {
            alerts += TelemetryAlert(
                snapshot.droneId, "ALTITUDE_EXCEEDED",
                "Altitude: ${"%.1f".format(snapshot.position.altitudeM)}m > ${maxAltitude}m",
                3
            )
        }

        alertHistory += alerts
        return alerts
    }

    fun alertCount() = alertHistory.size
    fun criticalCount() = alertHistory.count { it.severity == 3 }
}

// ===== Telemetry Processor =====

class AndroidTelemetryProcessor {
    private val buffer = TelemetryBuffer()
    private val alertEngine = TelemetryAlertEngine()
    private val listeners = mutableListOf<(TelemetrySnapshot) -> Unit>()

    fun addListener(listener: (TelemetrySnapshot) -> Unit) {
        listeners += listener
    }

    fun process(snapshot: TelemetrySnapshot): List<TelemetryAlert> {
        buffer.add(snapshot)
        listeners.forEach { it(snapshot) }
        return alertEngine.evaluate(snapshot)
    }

    fun fleetStats(): Map<String, Any> {
        val latest = buffer.latest()
        return mapOf(
            "buffered_records" to buffer.size(),
            "total_alerts" to alertEngine.alertCount(),
            "critical_alerts" to alertEngine.criticalCount(),
            "last_drone" to (latest?.droneId ?: "N/A"),
            "phase" to "613"
        )
    }
}

// ===== Network Client (Stub) =====

interface TelemetryApiClient {
    fun fetchTelemetry(droneId: String, callback: (TelemetrySnapshot?) -> Unit)
    fun streamTelemetry(droneIds: List<String>, onUpdate: (TelemetrySnapshot) -> Unit)
}

class HttpTelemetryClient(private val baseUrl: String = "http://localhost:8080") : TelemetryApiClient {
    override fun fetchTelemetry(droneId: String, callback: (TelemetrySnapshot?) -> Unit) {
        // Stub: simulate HTTP GET /api/v1/drones/{id}/telemetry
        val stub = TelemetrySnapshot(
            droneId = droneId,
            position = DronePosition(37.5665, 126.9780, 55.0),
            batteryPercent = 78.0,
            speedMs = 6.5,
            signalRssi = -68.0,
            cpuTemp = 42.0
        )
        callback(stub)
    }

    override fun streamTelemetry(droneIds: List<String>, onUpdate: (TelemetrySnapshot) -> Unit) {
        // Stub: would use WebSocket or SSE for real-time streaming
        droneIds.forEach { id -> fetchTelemetry(id) { it?.let(onUpdate) } }
    }
}

// ===== Main =====

fun main() {
    println("Phase 613: Android Telemetry Module")
    val processor = AndroidTelemetryProcessor()
    val client = HttpTelemetryClient()

    processor.addListener { snap ->
        println("  [TELEMETRY] ${snap.droneId}: bat=${snap.batteryPercent.roundToInt()}% alt=${"%.1f".format(snap.position.altitudeM)}m")
    }

    val droneIds = listOf("D001", "D002", "D003", "D004", "D005")
    droneIds.forEach { id ->
        client.fetchTelemetry(id) { snap ->
            snap?.let { processor.process(it).forEach { a -> println("  [ALERT] ${a.droneId}: ${a.message}") } }
        }
    }

    println("Fleet stats: ${processor.fleetStats()}")
}
