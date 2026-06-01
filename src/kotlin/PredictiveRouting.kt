// Phase 525: Predictive Routing — 드론 예측 라우팅 (Kotlin)
// Dijkstra-based predictive routing with traffic-aware cost functions.
package sdacs.routing

import java.util.PriorityQueue
import kotlin.math.sqrt
import kotlin.math.pow

const val PHASE = 525

// ── Graph structures ──────────────────────────────────────────────

data class Node(
    val id: Int,
    val x: Double,
    val y: Double,
    val z: Double
)

data class Edge(
    val from: Int,
    val to: Int,
    val baseCost: Double,
    var trafficLoad: Double = 0.0
)

// ── Traffic model ─────────────────────────────────────────────────

class TrafficModel(private val seed: Long = 42L) {
    private val rng = java.util.Random(seed)
    private val trafficMap = mutableMapOf<Pair<Int,Int>, Double>()

    fun getTraffic(from: Int, to: Int): Double =
        trafficMap.getOrPut(from to to) { rng.nextDouble() * 0.8 }

    fun updateTraffic(from: Int, to: Int, load: Double) {
        trafficMap[from to to] = load.coerceIn(0.0, 1.0)
    }

    fun effectiveCost(edge: Edge): Double =
        edge.baseCost * (1.0 + getTraffic(edge.from, edge.to) * 2.0)
}

// ── Dijkstra shortest-path ─────────────────────────────────────────

object Dijkstra {
    fun shortestPath(
        nodes: List<Node>,
        edges: List<Edge>,
        source: Int,
        target: Int,
        traffic: TrafficModel
    ): Pair<Double, List<Int>> {
        val n = nodes.size
        val dist = DoubleArray(n) { Double.MAX_VALUE }
        val prev = IntArray(n) { -1 }
        dist[source] = 0.0

        // (cost, nodeId)
        val pq = PriorityQueue<Pair<Double, Int>>(compareBy { it.first })
        pq.add(0.0 to source)

        val adj = buildAdjacency(edges, traffic)

        while (pq.isNotEmpty()) {
            val (d, u) = pq.poll()
            if (d > dist[u]) continue
            for ((v, cost) in (adj[u] ?: emptyList())) {
                val alt = dist[u] + cost
                if (alt < dist[v]) {
                    dist[v] = alt
                    prev[v] = u
                    pq.add(alt to v)
                }
            }
        }

        val path = mutableListOf<Int>()
        var cur = target
        while (cur != -1) {
            path.add(0, cur)
            cur = prev[cur]
        }
        return dist[target] to path
    }

    private fun buildAdjacency(
        edges: List<Edge>,
        traffic: TrafficModel
    ): Map<Int, List<Pair<Int, Double>>> {
        val adj = mutableMapOf<Int, MutableList<Pair<Int, Double>>>()
        for (e in edges) {
            val cost = traffic.effectiveCost(e)
            adj.getOrPut(e.from) { mutableListOf() }.add(e.to to cost)
            adj.getOrPut(e.to)  { mutableListOf() }.add(e.from to cost)
        }
        return adj
    }
}

// ── Predictive Router ─────────────────────────────────────────────

class PredictiveRouting(
    private val nodes: List<Node>,
    private val edges: List<Edge>,
    private val traffic: TrafficModel = TrafficModel(42L)
) {
    fun route(from: Int, to: Int): Pair<Double, List<Int>> =
        Dijkstra.shortestPath(nodes, edges, from, to, traffic)

    fun updateTraffic(from: Int, to: Int, load: Double) =
        traffic.updateTraffic(from, to, load)

    fun euclidean(a: Node, b: Node): Double =
        sqrt((a.x-b.x).pow(2) + (a.y-b.y).pow(2) + (a.z-b.z).pow(2))
}

// ── Factory helpers ────────────────────────────────────────────────

fun buildGrid(rows: Int, cols: Int): Pair<List<Node>, List<Edge>> {
    val nodes = (0 until rows * cols).map { i ->
        Node(i, (i % cols) * 50.0, (i / cols) * 50.0, 50.0)
    }
    val edges = mutableListOf<Edge>()
    for (r in 0 until rows) {
        for (c in 0 until cols) {
            val id = r * cols + c
            if (c + 1 < cols) edges.add(Edge(id, id + 1, 50.0))
            if (r + 1 < rows) edges.add(Edge(id, id + cols, 50.0))
        }
    }
    return nodes to edges
}

// ── Entry point ────────────────────────────────────────────────────

fun main() {
    println("Phase $PHASE: Predictive Routing — 드론 예측 경로 계획 (Dijkstra + Traffic)")
    val (nodes, edges) = buildGrid(5, 5)
    val router = PredictiveRouting(nodes, edges)

    val (cost, path) = router.route(0, 24)
    println("Route 0→24: cost=%.2f path=%s".format(cost, path))

    // Simulate traffic update and re-route
    router.updateTraffic(0, 1, 0.9)
    val (cost2, path2) = router.route(0, 24)
    println("After traffic update: cost=%.2f path=%s".format(cost2, path2))
    println("Phase $PHASE complete.")
}
