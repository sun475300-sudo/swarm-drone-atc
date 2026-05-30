// Phase 613: android_telemetry — Kotlin/Android 기반 텔레메트리 앱
// SDACS Android Telemetry Application

package com.sdacs.android

import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import java.net.URI
import kotlin.math.*

// 드론 상태 데이터 클래스
data class DroneStatus(
    val droneId: Int,
    val lat: Double,
    val lon: Double,
    val alt: Double,
    val battery: Double,
    val speed: Double,
    val flightMode: String,
    val isArmed: Boolean,
    val timestamp: Long = System.currentTimeMillis()
)

// 공역 스냅샷
data class AirspaceSnapshot(
    val drones: List<DroneStatus>,
    val conflictCount: Int,
    val resolutionRate: Double,
    val timestamp: Long
)

// 텔레메트리 이벤트 봉인 클래스
sealed class TelemetryEvent {
    data class SnapshotReceived(val snapshot: AirspaceSnapshot) : TelemetryEvent()
    data class ConnectionChanged(val connected: Boolean) : TelemetryEvent()
    data class ErrorOccurred(val message: String) : TelemetryEvent()
    data class ConflictAlert(val droneId1: Int, val droneId2: Int, val separation: Double) : TelemetryEvent()
}

// 텔레메트리 저장소 인터페이스
interface TelemetryRepository {
    fun observeSnapshots(): Flow<AirspaceSnapshot>
    suspend fun getLatestSnapshot(): AirspaceSnapshot?
    suspend fun sendCommand(droneId: Int, command: String, params: Map<String, Any> = emptyMap()): Boolean
}

// WebSocket 기반 텔레메트리 서비스
class WebSocketTelemetryService(
    private val wsUrl: String,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
) : TelemetryRepository {

    private val _snapshots = MutableSharedFlow<AirspaceSnapshot>(replay = 1)
    private var isConnected = false
    private var reconnectDelay = 1000L

    override fun observeSnapshots(): Flow<AirspaceSnapshot> = _snapshots.asSharedFlow()

    override suspend fun getLatestSnapshot(): AirspaceSnapshot? = _snapshots.replayCache.firstOrNull()

    override suspend fun sendCommand(
        droneId: Int,
        command: String,
        params: Map<String, Any>
    ): Boolean {
        println("[Telemetry] Command: drone=$droneId cmd=$command params=$params")
        return true
    }

    fun connect() {
        scope.launch {
            while (isActive) {
                try {
                    println("[WebSocket] Connecting to $wsUrl")
                    isConnected = true
                    reconnectDelay = 1000L
                    // WebSocket 연결 루프 (실제 구현에서는 OkHttp WebSocket 사용)
                    delay(Long.MAX_VALUE)
                } catch (e: Exception) {
                    isConnected = false
                    println("[WebSocket] Disconnected: ${e.message}")
                    delay(reconnectDelay)
                    reconnectDelay = minOf(reconnectDelay * 2, 30000L)
                }
            }
        }
    }

    fun disconnect() {
        isConnected = false
        scope.cancel()
    }
}

// 배터리 수준 계산 유틸리티
object BatteryUtils {
    fun getBatteryLevel(pct: Double): BatteryLevel = when {
        pct >= 50.0 -> BatteryLevel.GOOD
        pct >= 20.0 -> BatteryLevel.LOW
        else -> BatteryLevel.CRITICAL
    }

    enum class BatteryLevel { GOOD, LOW, CRITICAL }
}

// 거리 계산 (Haversine)
object GeoUtils {
    private const val EARTH_RADIUS_M = 6371000.0

    fun haversineDistance(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = sin(dLat / 2).pow(2) +
                cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLon / 2).pow(2)
        return 2.0 * EARTH_RADIUS_M * atan2(sqrt(a), sqrt(1 - a))
    }

    fun detectConflicts(drones: List<DroneStatus>, minSep: Double = 5.0): List<Pair<Int, Int>> {
        val conflicts = mutableListOf<Pair<Int, Int>>()
        for (i in drones.indices) {
            for (j in (i + 1) until drones.size) {
                val dist = haversineDistance(
                    drones[i].lat, drones[i].lon,
                    drones[j].lat, drones[j].lon
                )
                val altDiff = abs(drones[i].alt - drones[j].alt)
                val sep3d = sqrt(dist.pow(2) + altDiff.pow(2))
                if (sep3d < minSep) {
                    conflicts.add(Pair(drones[i].droneId, drones[j].droneId))
                }
            }
        }
        return conflicts
    }
}

// Phase 613 메인
fun main() {
    println("SDACS Android Telemetry Module — Phase 613")
    val service = WebSocketTelemetryService("ws://localhost:8765")
    println("Service created: ${service != null}")

    val drones = listOf(
        DroneStatus(0, 37.5, 127.0, 50.0, 85.0, 5.0, "GUIDED", true),
        DroneStatus(1, 37.5, 127.0, 52.0, 90.0, 5.0, "GUIDED", true),
    )
    val conflicts = GeoUtils.detectConflicts(drones)
    println("Conflict check: ${conflicts.size} conflicts detected")
    println("Battery D0: ${BatteryUtils.getBatteryLevel(drones[0].battery)}")
}
