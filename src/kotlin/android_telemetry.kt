/**
 * android_telemetry.kt
 * Kotlin Android stub for drone telemetry reception and display.
 * Uses Retrofit for HTTP calls and LiveData for UI binding.
 */

package com.sdacs.android.telemetry

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

// ---------------------------------------------------------------------------
// Data models
// ---------------------------------------------------------------------------

data class DronePosition(
    val x: Double,
    val y: Double,
    val z: Double
)

data class DroneTelemetry(
    val droneId: String,
    val position: DronePosition,
    val velocityMs: Double,
    val batteryPct: Int,
    val state: String
)

data class ApiResponse<T>(
    val success: Boolean,
    val data: T
)

// ---------------------------------------------------------------------------
// Repository (stub — replace with Retrofit interface)
// ---------------------------------------------------------------------------

class TelemetryRepository {
    private val baseUrl = "http://10.0.2.2:3000/api"  // localhost from Android emulator

    suspend fun fetchDrones(): List<DroneTelemetry> {
        // TODO: implement Retrofit call to $baseUrl/drones
        return emptyList()
    }

    suspend fun fetchAlerts(): List<String> {
        // TODO: implement Retrofit call to $baseUrl/alerts
        return emptyList()
    }
}

// ---------------------------------------------------------------------------
// ViewModel
// ---------------------------------------------------------------------------

class TelemetryViewModel : ViewModel() {
    private val repository = TelemetryRepository()

    private val _drones = MutableLiveData<List<DroneTelemetry>>(emptyList())
    val drones: LiveData<List<DroneTelemetry>> = _drones

    private val _alerts = MutableLiveData<List<String>>(emptyList())
    val alerts: LiveData<List<String>> = _alerts

    init {
        startPolling()
    }

    private fun startPolling() {
        viewModelScope.launch {
            while (true) {
                _drones.value = repository.fetchDrones()
                _alerts.value = repository.fetchAlerts()
                delay(1_000L)
            }
        }
    }
}
