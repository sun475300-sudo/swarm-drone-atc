/**
 * Phase 325: Kotlin Dynamic Spectrum Manager
 * Cognitive radio channel sensing, spectrum hole detection,
 * dynamic allocation with DSL-friendly API.
 */

package sdacs.spectrum

import kotlin.math.*

// ── Types ──────────────────────────────────────────────────────────
enum class ChannelStatus { IDLE, OCCUPIED, SENSING, TRANSMITTING }
enum class SpectrumBand { ISM_2_4GHZ, ISM_5GHZ, CBRS, TVWS }

data class Channel(
    val channelId: String,
    val centerFreqMhz: Double,
    val bandwidthMhz: Double,
    val band: SpectrumBand,
    var status: ChannelStatus = ChannelStatus.IDLE,
    var primaryUserActive: Boolean = false,
    var snrDb: Double = 20.0,
    var lastSensed: Double = 0.0,
)

data class SpectrumHole(
    val channelId: String,
    val startTime: Double,
    val predictedDuration: Double,
    val availability: Double,
    val capacityMbps: Double,
)

data class Allocation(
    val droneId: String,
    val channelId: String,
    val startTime: Double,
    val dataRateMbps: Double,
)

// ── Spectrum Manager ───────────────────────────────────────────────
class SpectrumManager(private val seed: Long = 42L) {
    private val random = java.util.Random(seed)
    private val channels = mutableMapOf<String, Channel>()
    private val allocations = mutableMapOf<String, Allocation>()
    private val sensingHistory = mutableMapOf<String, MutableList<Double>>()

    companion object {
        const val NOISE_FLOOR_DBM = -100.0
        const val DETECTION_THRESHOLD = -80.0
    }

    fun initDefaultChannels() {
        listOf(
            Channel("ch1", 2412.0, 20.0, SpectrumBand.ISM_2_4GHZ),
            Channel("ch6", 2437.0, 20.0, SpectrumBand.ISM_2_4GHZ),
            Channel("ch11", 2462.0, 20.0, SpectrumBand.ISM_2_4GHZ),
            Channel("ch36", 5180.0, 40.0, SpectrumBand.ISM_5GHZ),
            Channel("ch44", 5220.0, 40.0, SpectrumBand.ISM_5GHZ),
            Channel("cbrs1", 3550.0, 10.0, SpectrumBand.CBRS),
            Channel("tvws1", 600.0, 6.0, SpectrumBand.TVWS),
        ).forEach { channels[it.channelId] = it }
    }

    fun senseChannel(channelId: String, timestamp: Double): Double {
        val ch = channels[channelId] ?: return 0.0
        ch.status = ChannelStatus.SENSING
        ch.lastSensed = timestamp

        val noise = random.nextGaussian() * 3.0
        val energy = if (ch.primaryUserActive) -60.0 + noise else NOISE_FLOOR_DBM + noise
        ch.snrDb = energy - NOISE_FLOOR_DBM
        ch.status = if (energy > DETECTION_THRESHOLD) ChannelStatus.OCCUPIED else ChannelStatus.IDLE

        sensingHistory.getOrPut(channelId) { mutableListOf() }.add(energy)
        return energy
    }

    fun senseAll(timestamp: Double): Map<String, Double> =
        channels.keys.associateWith { senseChannel(it, timestamp) }

    fun detectHoles(timestamp: Double): List<SpectrumHole> =
        channels.values.filter { it.status == ChannelStatus.IDLE }.map { ch ->
            val history = sensingHistory[ch.channelId] ?: emptyList()
            val idleRatio = if (history.size >= 3)
                history.takeLast(10).count { it < DETECTION_THRESHOLD } / minOf(history.size, 10).toDouble()
            else 0.5

            val capacity = ch.bandwidthMhz * log2(1.0 + 10.0.pow(ch.snrDb / 10.0))

            SpectrumHole(
                channelId = ch.channelId,
                startTime = timestamp,
                predictedDuration = idleRatio * 10.0,
                availability = idleRatio,
                capacityMbps = capacity,
            )
        }

    fun allocateChannel(droneId: String, timestamp: Double): Allocation? {
        val holes = detectHoles(timestamp)
        if (holes.isEmpty()) return null

        val best = holes.maxByOrNull { it.capacityMbps * it.availability } ?: return null
        channels[best.channelId]?.status = ChannelStatus.TRANSMITTING

        val alloc = Allocation(droneId, best.channelId, timestamp, best.capacityMbps)
        allocations[droneId] = alloc
        return alloc
    }

    fun releaseChannel(droneId: String) {
        allocations.remove(droneId)?.let { alloc ->
            channels[alloc.channelId]?.status = ChannelStatus.IDLE
        }
    }

    fun setPrimaryUser(channelId: String, active: Boolean) {
        channels[channelId]?.let { ch ->
            ch.primaryUserActive = active
            if (active) {
                ch.status = ChannelStatus.OCCUPIED
                allocations.entries.removeAll { it.value.channelId == channelId }
            }
        }
    }

    fun summary(): Map<String, Any> {
        val idle = channels.values.count { it.status == ChannelStatus.IDLE }
        return mapOf(
            "totalChannels" to channels.size,
            "idleChannels" to idle,
            "activeAllocations" to allocations.size,
            "sensingEvents" to sensingHistory.values.sumOf { it.size },
        )
    }
}

fun main() {
    val mgr = SpectrumManager()
    mgr.initDefaultChannels()
    mgr.senseAll(1.0)

    val alloc = mgr.allocateChannel("drone_1", 1.0)
    println("Allocation: $alloc")
    println("Summary: ${mgr.summary()}")
}
