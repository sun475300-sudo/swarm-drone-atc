// Phase 613: Android Telemetry — Kotlin Parser
// Android 텔레메트리 수집 파서

package com.sdacs.telemetry

data class TelemetryFrame(
    val droneId: String,
    val timestamp: Long,
    val latitude: Double,
    val longitude: Double,
    val altitude: Double,
    val speed: Double,
    val heading: Double,
    val battery: Double,
    val rssi: Int,
    val satellites: Int
)

data class ParseResult(
    val frames: List<TelemetryFrame>,
    val errors: Int,
    val bytesProcessed: Long
)

class TelemetryParser {
    private val frameBuffer = mutableListOf<TelemetryFrame>()
    private var errorCount = 0
    private var totalBytes = 0L

    companion object {
        const val HEADER_MAGIC = 0xSD.toByte()
        const val FRAME_SIZE = 64
        const val MAX_BUFFER = 1000
    }

    fun parseFrame(data: ByteArray, offset: Int = 0): TelemetryFrame? {
        if (data.size - offset < FRAME_SIZE) {
            errorCount++
            return null
        }

        totalBytes += FRAME_SIZE

        return try {
            TelemetryFrame(
                droneId = "drone_${data[offset + 1].toInt() and 0xFF}",
                timestamp = System.currentTimeMillis(),
                latitude = decodeDouble(data, offset + 8),
                longitude = decodeDouble(data, offset + 16),
                altitude = decodeDouble(data, offset + 24),
                speed = decodeDouble(data, offset + 32),
                heading = decodeDouble(data, offset + 40),
                battery = (data[offset + 48].toInt() and 0xFF) / 255.0,
                rssi = -(data[offset + 49].toInt() and 0xFF),
                satellites = data[offset + 50].toInt() and 0xFF
            )
        } catch (e: Exception) {
            errorCount++
            null
        }
    }

    fun processBatch(data: ByteArray): ParseResult {
        val frames = mutableListOf<TelemetryFrame>()
        var offset = 0

        while (offset + FRAME_SIZE <= data.size) {
            parseFrame(data, offset)?.let { frame ->
                frames.add(frame)
                frameBuffer.add(frame)
                if (frameBuffer.size > MAX_BUFFER) {
                    frameBuffer.removeAt(0)
                }
            }
            offset += FRAME_SIZE
        }

        return ParseResult(frames, errorCount, totalBytes)
    }

    fun getLatestFrames(count: Int = 10): List<TelemetryFrame> {
        return frameBuffer.takeLast(count)
    }

    fun getDroneIds(): Set<String> {
        return frameBuffer.map { it.droneId }.toSet()
    }

    fun getAverageBattery(): Double {
        if (frameBuffer.isEmpty()) return 0.0
        return frameBuffer.map { it.battery }.average()
    }

    private fun decodeDouble(data: ByteArray, offset: Int): Double {
        var bits: Long = 0
        for (i in 0 until 8) {
            bits = bits or ((data[offset + i].toLong() and 0xFF) shl (i * 8))
        }
        return Double.fromBits(bits)
    }

    fun reset() {
        frameBuffer.clear()
        errorCount = 0
        totalBytes = 0
    }
}
