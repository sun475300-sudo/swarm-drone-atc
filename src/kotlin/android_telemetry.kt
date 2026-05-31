// Android Telemetry — SDACS Phase 613
package com.sdacs.telemetry

data class DroneStatus(
    val id: String,
    val lat: Double,
    val lon: Double,
    val alt: Double,
    val battery: Int
)

class TelemetryManager {
    suspend fun fetchDrones(): List<DroneStatus> = emptyList()
    fun formatDrone(d: DroneStatus): String = "[${d.id}] ${d.lat},${d.lon}"
}
