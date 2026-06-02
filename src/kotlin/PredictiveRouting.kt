// Phase 525: Predictive Routing — Kotlin
// SDACS Dijkstra-based predictive route planning with traffic awareness

package sdacs.routing

import java.util.PriorityQueue
import kotlin.math.sqrt
import kotlin.math.abs

// Phase 525 marker — Dijkstra predictive routing with traffic model

data class Node(
    val id: String,
    val lat: Double,
    val lon: Double,
    val alt: Double = 60.0
)

data class Edge(
    val from: String,
    val to: String,
    val baseDistance: Double,
    var trafficFactor: Double = 1.0  // >1 = congested
)

data class Route(
    val nodes: List<String>,
    val totalCost: Double,
    val estimatedTimeSec: Double,
    val trafficScore: Double
)

class TrafficModel {
    private val congestion = mutableMapOf<String, Double>()

    fun updateTraffic(edgeKey: String, factor: Double) {
        congestion[edgeKey] = factor.coerceIn(0.5, 5.0)
    }

    fun getTrafficFactor(from: String, to: String): Double {
        return congestion["$from->$to"] ?: 1.0
    }

    fun predictTraffic(from: String, to: String, futureSeconds: Double): Double {
        val current = getTrafficFactor(from, to)
        // Simple decay model: traffic normalizes over time
        return 1.0 + (current - 1.0) * Math.exp(-futureSeconds / 300.0)
    }
}

class RouteGraph {
    private val nodes = mutableMapOf<String, Node>()
    private val adjacency = mutableMapOf<String, MutableList<Edge>>()

    fun addNode(node: Node) {
        nodes[node.id] = node
        adjacency.getOrPut(node.id) { mutableListOf() }
    }

    fun addEdge(from: String, to: String, bidirectional: Boolean = true) {
        val fromNode = nodes[from] ?: return
        val toNode   = nodes[to]   ?: return
        val dist     = haversineDistance(fromNode, toNode)

        adjacency.getOrPut(from) { mutableListOf() }.add(Edge(from, to, dist))
        if (bidirectional) {
            adjacency.getOrPut(to) { mutableListOf() }.add(Edge(to, from, dist))
        }
    }

    fun getNeighbors(nodeId: String): List<Edge> = adjacency[nodeId] ?: emptyList()

    fun getNode(id: String): Node? = nodes[id]

    fun nodeCount(): Int = nodes.size

    fun edgeCount(): Int = adjacency.values.sumOf { it.size }

    private fun haversineDistance(a: Node, b: Node): Double {
        val earthR = 6_371_000.0
        val lat1   = Math.toRadians(a.lat)
        val lat2   = Math.toRadians(b.lat)
        val dLat   = Math.toRadians(b.lat - a.lat)
        val dLon   = Math.toRadians(b.lon - a.lon)
        val sinLat = Math.sin(dLat / 2)
        val sinLon = Math.sin(dLon / 2)
        val h = sinLat * sinLat + Math.cos(lat1) * Math.cos(lat2) * sinLon * sinLon
        return earthR * 2 * Math.atan2(sqrt(h), sqrt(1 - h))
    }
}

class PredictiveRouter(
    private val graph: RouteGraph,
    private val traffic: TrafficModel = TrafficModel()
) {
    private data class DijkstraNode(
        val id: String,
        val cost: Double,
        val parent: String?
    ) : Comparable<DijkstraNode> {
        override fun compareTo(other: DijkstraNode) = cost.compareTo(other.cost)
    }

    /**
     * Dijkstra shortest path with traffic-aware edge costs.
     */
    fun findRoute(
        start: String,
        goal: String,
        droneSpeed: Double = 10.0,
        departureDelaySec: Double = 0.0
    ): Route? {
        val dist    = mutableMapOf<String, Double>().withDefault { Double.MAX_VALUE }
        val parent  = mutableMapOf<String, String?>()
        val pq      = PriorityQueue<DijkstraNode>()

        dist[start] = 0.0
        pq.add(DijkstraNode(start, 0.0, null))

        while (pq.isNotEmpty()) {
            val curr = pq.poll()
            if (curr.cost > (dist[curr.id] ?: Double.MAX_VALUE)) continue
            parent[curr.id] = curr.parent

            if (curr.id == goal) break

            for (edge in graph.getNeighbors(curr.id)) {
                val travelTime = edge.baseDistance / droneSpeed
                val tf = traffic.predictTraffic(edge.from, edge.to,
                                                 departureDelaySec + travelTime)
                val edgeCost = edge.baseDistance * tf
                val newCost  = curr.cost + edgeCost
                if (newCost < (dist[edge.to] ?: Double.MAX_VALUE)) {
                    dist[edge.to] = newCost
                    pq.add(DijkstraNode(edge.to, newCost, curr.id))
                }
            }
        }

        if (!parent.containsKey(goal)) return null

        // Reconstruct path
        val path = mutableListOf<String>()
        var current: String? = goal
        while (current != null) {
            path.add(current)
            current = parent[current]
        }
        path.reverse()

        val totalDist = dist[goal] ?: return null
        val eta       = totalDist / droneSpeed

        return Route(
            nodes            = path,
            totalCost        = totalDist,
            estimatedTimeSec = eta,
            trafficScore     = totalDist / (path.size * 100.0)
        )
    }

    fun updateTraffic(from: String, to: String, factor: Double) {
        traffic.updateTraffic("$from->$to", factor)
    }
}

// Demo
fun main() {
    val g = RouteGraph()
    listOf("A","B","C","D","E").forEachIndexed { i, id ->
        g.addNode(Node(id, 37.5665 + i * 0.001, 126.978 + i * 0.001))
    }
    g.addEdge("A","B"); g.addEdge("B","C"); g.addEdge("C","D")
    g.addEdge("A","C"); g.addEdge("B","D"); g.addEdge("D","E")

    val router = PredictiveRouter(g)
    val route  = router.findRoute("A", "E")
    println("Phase 525: Dijkstra route A->E: ${route?.nodes}")
    println("ETA: ${route?.estimatedTimeSec?.toLong()}s")
}
