// SDACS Android Telemetry — Kotlin (Phase 613)
// 드론 군집 Android 텔레메트리 클라이언트

package sdacs.android

import kotlin.math.sqrt
import kotlin.math.pow

data class TelemetryPacket(
    val droneId: String,
    val x: Double,
    val y: Double,
    val z: Double,
    val vx: Double,
    val vy: Double,
    val vz: Double,
    val battery: Double,
    val state: String,
    val timestamp: Long = System.currentTimeMillis()
)

data class TelemetryStats(
    val packetCount: Long,
    val avgBattery: Double,
    val avgAltitude: Double,
    val activeDrones: Int,
    val lowBatteryCount: Int
)

// 텔레메트리 수신기 (Phase 613)
class TelemetryReceiver {
    private val latest = mutableMapOf<String, TelemetryPacket>()
    private var totalPackets = 0L
    private val listeners = mutableListOf<(TelemetryPacket) -> Unit>()

    fun onPacket(packet: TelemetryPacket) {
        latest[packet.droneId] = packet
        totalPackets++
        listeners.forEach { it(packet) }
    }

    fun addListener(listener: (TelemetryPacket) -> Unit) {
        listeners.add(listener)
    }

    fun removeListener(listener: (TelemetryPacket) -> Unit) {
        listeners.remove(listener)
    }

    fun getStats(): TelemetryStats {
        val packets = latest.values.toList()
        val n = packets.size
        return TelemetryStats(
            packetCount = totalPackets,
            avgBattery = if (n > 0) packets.sumOf { it.battery } / n else 0.0,
            avgAltitude = if (n > 0) packets.sumOf { it.z } / n else 0.0,
            activeDrones = packets.count { it.state in setOf("FLYING", "HOVERING") },
            lowBatteryCount = packets.count { it.battery < 20.0 }
        )
    }

    fun getLatest(droneId: String): TelemetryPacket? = latest[droneId]
    fun getAllLatest(): List<TelemetryPacket> = latest.values.toList()
    fun droneCount(): Int = latest.size
}

// Android ViewModel 기반 상태 관리
class TelemetryViewModel {
    val receiver = TelemetryReceiver()
    private val _conflicts = mutableListOf<Pair<String, String>>()
    val conflicts: List<Pair<String, String>> get() = _conflicts

    private val separationThreshold = 50.0

    init {
        receiver.addListener { updateConflicts() }
    }

    private fun updateConflicts() {
        val packets = receiver.getAllLatest()
        _conflicts.clear()
        for (i in packets.indices) {
            for (j in (i + 1) until packets.size) {
                val a = packets[i]; val b = packets[j]
                val dist = sqrt((a.x - b.x).pow(2) + (a.y - b.y).pow(2) + (a.z - b.z).pow(2))
                if (dist < separationThreshold) _conflicts.add(a.droneId to b.droneId)
            }
        }
    }

    fun ingest(packet: TelemetryPacket) = receiver.onPacket(packet)
    fun stats() = receiver.getStats()
    fun hasConflicts() = _conflicts.isNotEmpty()
}

// WebSocket 연결 관리자
class WebSocketManager(private val url: String) {
    private var connected = false
    private var messageCount = 0L

    fun connect(): Boolean {
        connected = true
        return true
    }

    fun disconnect() { connected = false }

    fun send(data: String): Boolean {
        if (!connected) return false
        messageCount++
        return true
    }

    val isConnected: Boolean get() = connected
    val sentCount: Long get() = messageCount
}
