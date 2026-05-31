// SDACS Phase 613 — Android telemetry client (Kotlin/OkHttp)
package com.sdacs.telemetry
data class DroneState(val id: String, val lat: Double, val lon: Double, val alt: Double, val battery: Double)
class TelemetryClient(private val url: String) {
    fun connect(onUpdate: (List<DroneState>) -> Unit) { /* OkHttp WebSocket */ }
}
