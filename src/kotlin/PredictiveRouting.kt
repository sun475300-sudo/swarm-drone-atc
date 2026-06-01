// Phase 525 — Predictive Routing with Dijkstra and Traffic Awareness
// Kotlin module for swarm drone route planning with real-time traffic modeling.

package swarm.routing

import java.util.PriorityQueue
import kotlin.math.sqrt

/**
 * Traffic state for a given airspace segment.
 */
data class TrafficState(
    val segmentId: String,
    val congestionLevel: Double,  // 0.0 = free, 1.0 = fully blocked
    val windSpeed: Double,
    val timestamp: Long
)

/**
 * A node in the routing graph representing a waypoint.
 */
data class RouteNode(
    val id: String,
    val x: Double,
    val y: Double,
    val z: Double
)

/**
 * An edge in the routing graph with traffic-adjusted cost.
 */
data class RouteEdge(
    val from: String,
    val to: String,
    val baseDistance: Double,
    val trafficPenalty: Double = 0.0
) {
    val effectiveCost: Double get() = baseDistance * (1.0 + trafficPenalty)
}

/**
 * Result of a Dijkstra route calculation.
 */
data class RouteResult(
    val path: List<String>,
    val totalCost: Double,
    val trafficAdjusted: Boolean
)

/**
 * Traffic monitor that tracks congestion on airspace segments.
 */
class TrafficMonitor {
    private val trafficMap = mutableMapOf<String, TrafficState>()

    fun updateTraffic(state: TrafficState) {
        trafficMap[state.segmentId] = state
    }

    fun getCongestion(segmentId: String): Double {
        return trafficMap[segmentId]?.congestionLevel ?: 0.0
    }

    fun getTrafficPenalty(from: String, to: String): Double {
        val key = "${from}->${to}"
        return getCongestion(key) * 2.0  // traffic doubles effective cost at full congestion
    }

    fun summary(): Map<String, Any> {
        val avgCongestion = if (trafficMap.isEmpty()) 0.0
        else trafficMap.values.map { it.congestionLevel }.average()
        return mapOf(
            "monitored_segments" to trafficMap.size,
            "avg_congestion" to avgCongestion
        )
    }
}

/**
 * PredictiveRouting — Dijkstra-based drone path planner with traffic awareness.
 * Phase 525: Implements shortest path with real-time traffic cost adjustments.
 */
class PredictiveRouting(private val trafficMonitor: TrafficMonitor = TrafficMonitor()) {
    private val nodes = mutableMapOf<String, RouteNode>()
    private val adjacency = mutableMapOf<String, MutableList<RouteEdge>>()

    fun addNode(node: RouteNode) {
        nodes[node.id] = node
        adjacency.getOrPut(node.id) { mutableListOf() }
    }

    fun addEdge(edge: RouteEdge) {
        adjacency.getOrPut(edge.from) { mutableListOf() }.add(edge)
        // Bidirectional
        adjacency.getOrPut(edge.to) { mutableListOf() }.add(
            edge.copy(from = edge.to, to = edge.from)
        )
    }

    /**
     * Dijkstra's algorithm with traffic-aware edge costs.
     * Returns the shortest path from source to destination.
     */
    fun dijkstra(source: String, destination: String): RouteResult {
        val dist = mutableMapOf<String, Double>().withDefault { Double.MAX_VALUE }
        val prev = mutableMapOf<String, String?>()
        val visited = mutableSetOf<String>()

        dist[source] = 0.0
        // PriorityQueue sorted by distance: (cost, nodeId)
        val pq = PriorityQueue<Pair<Double, String>>(compareBy { it.first })
        pq.add(Pair(0.0, source))

        while (pq.isNotEmpty()) {
            val (cost, current) = pq.poll()
            if (current in visited) continue
            visited.add(current)
            if (current == destination) break

            for (edge in adjacency[current] ?: emptyList()) {
                val trafficPenalty = trafficMonitor.getTrafficPenalty(edge.from, edge.to)
                val adjustedCost = edge.baseDistance * (1.0 + trafficPenalty)
                val newDist = cost + adjustedCost
                if (newDist < dist.getValue(edge.to)) {
                    dist[edge.to] = newDist
                    prev[edge.to] = current
                    pq.add(Pair(newDist, edge.to))
                }
            }
        }

        val path = reconstructPath(prev, source, destination)
        return RouteResult(
            path = path,
            totalCost = dist.getValue(destination),
            trafficAdjusted = true
        )
    }

    private fun reconstructPath(prev: Map<String, String?>, source: String, dest: String): List<String> {
        val path = mutableListOf<String>()
        var current: String? = dest
        while (current != null) {
            path.add(0, current)
            current = prev[current]
        }
        return if (path.firstOrNull() == source) path else emptyList()
    }

    fun buildDefaultGraph(nodeCount: Int) {
        for (i in 0 until nodeCount) {
            addNode(RouteNode("N$i", i * 10.0, (i % 3) * 5.0, 50.0))
        }
        for (i in 0 until nodeCount - 1) {
            val dist = sqrt(100.0 + 25.0)
            addEdge(RouteEdge("N$i", "N${i + 1}", dist))
        }
    }
}

fun main() {
    println("Phase 525: PredictiveRouting with Dijkstra + Traffic")
    val monitor = TrafficMonitor()
    monitor.updateTraffic(TrafficState("N0->N1", 0.3, 5.0, System.currentTimeMillis()))

    val router = PredictiveRouting(monitor)
    router.buildDefaultGraph(8)

    val result = router.dijkstra("N0", "N7")
    println("Route: ${result.path.joinToString(" -> ")}")
    println("Total cost: ${"%.2f".format(result.totalCost)}")
    println("Traffic summary: ${monitor.summary()}")
}
