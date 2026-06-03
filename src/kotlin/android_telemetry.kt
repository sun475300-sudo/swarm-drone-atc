// Phase 613: Android Telemetry — Kotlin
// SDACS Android app for drone telemetry display

package sdacs.android

data class TelemetryData(
    val droneId:   String,
    val latitude:  Double,
    val longitude: Double,
    val altitude:  Double,
    val speed:     Double,
    val battery:   Double,
    val timestamp: Long = System.currentTimeMillis()
)

class TelemetryRepository {
    private val cache = mutableMapOf<String, TelemetryData>()

    fun update(data: TelemetryData) { cache[data.droneId] = data }
    fun getAll(): List<TelemetryData> = cache.values.toList()
    fun get(droneId: String): TelemetryData? = cache[droneId]
}
