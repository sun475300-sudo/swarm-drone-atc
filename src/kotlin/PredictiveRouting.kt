// P525: PredictiveRouting - Kotlin Dijkstra-based predictive routing
// Phase 525: Traffic-aware path planning for drone fleet management

package com.sdacs.routing

import kotlin.math.sqrt

data class Node(
    val id: String,
    val x: Double,
    val y: Double,
    val z: Double,
    val trafficLoad: Double = 0.0
)

data class Edge(
    val from: String,
    val to: String,
    val weight: Double,
    val trafficFactor: Double = 1.0
)

data class RouteResult(
    val path: List<String>,
    val totalCost: Double,
    val estimatedTime: Double,
    val trafficPenalty: Double
)

class PredictiveRouter {
    private val nodes: MutableMap<String, Node> = mutableMapOf()
    private val adjacency: MutableMap<String, MutableList<Edge>> = mutableMapOf()

    fun addNode(node: Node) {
        nodes[node.id] = node
        adjacency.getOrPut(node.id) { mutableListOf() }
    }

    fun addEdge(edge: Edge) {
        adjacency.getOrPut(edge.from) { mutableListOf() }.add(edge)
        adjacency.getOrPut(edge.to) { mutableListOf() }.add(
            Edge(edge.to, edge.from, edge.weight, edge.trafficFactor)
        )
    }

    // Dijkstra's algorithm with traffic-awareness
    fun dijkstra(start: String, end: String): RouteResult? {
        val dist = mutableMapOf<String, Double>().withDefault { Double.MAX_VALUE }
        val prev = mutableMapOf<String, String?>()
        val visited = mutableSetOf<String>()
        val queue = sortedSetOf<Pair<Double, String>>(compareBy({ it.first }, { it.second }))

        dist[start] = 0.0
        queue.add(0.0 to start)

        while (queue.isNotEmpty()) {
            val (d, u) = queue.first()
            queue.remove(queue.first())
            if (u in visited) continue
            visited.add(u)
            if (u == end) break

            for (edge in adjacency[u] ?: emptyList()) {
                val traffic = nodes[edge.to]?.trafficLoad ?: 0.0
                val cost = edge.weight * edge.trafficFactor * (1.0 + traffic)
                val newDist = d + cost
                if (newDist < (dist[edge.to] ?: Double.MAX_VALUE)) {
                    dist[edge.to] = newDist
                    prev[edge.to] = u
                    queue.add(newDist to edge.to)
                }
            }
        }

        val totalCost = dist[end] ?: return null
        val path = buildPath(prev, start, end)
        val trafficPenalty = path.sumOf { nodes[it]?.trafficLoad ?: 0.0 }
        return RouteResult(path, totalCost, totalCost / 15.0, trafficPenalty)
    }

    private fun buildPath(prev: Map<String, String?>, start: String, end: String): List<String> {
        val path = mutableListOf<String>()
        var current: String? = end
        while (current != null) {
            path.add(0, current)
            current = prev[current]
        }
        return if (path.first() == start) path else emptyList()
    }

    fun updateTraffic(nodeId: String, load: Double) {
        nodes[nodeId]?.let { nodes[nodeId] = it.copy(trafficLoad = load.coerceIn(0.0, 1.0)) }
    }

    fun predictTraffic(nodeId: String, futureTimeStep: Int): Double {
        val base = nodes[nodeId]?.trafficLoad ?: 0.0
        return (base * 0.9 + 0.05 * futureTimeStep).coerceIn(0.0, 1.0)
    }
}

fun buildSampleAirspaceGraph(gridSize: Int = 5): PredictiveRouter {
    val router = PredictiveRouter()
    for (i in 0 until gridSize) {
        for (j in 0 until gridSize) {
            router.addNode(Node("${i}_${j}", i * 200.0, j * 200.0, 60.0))
        }
    }
    for (i in 0 until gridSize) {
        for (j in 0 until gridSize) {
            if (i + 1 < gridSize) router.addEdge(Edge("${i}_${j}", "${i+1}_${j}", 200.0))
            if (j + 1 < gridSize) router.addEdge(Edge("${i}_${j}", "${i}_${j+1}", 200.0))
        }
    }
    return router
}
