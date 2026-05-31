// PredictiveRouting.kt - Predictive routing for SDACS drone fleet (Phase 525)
// Dijkstra-based routing with traffic prediction

package com.sdacs.routing

import kotlin.math.sqrt

data class Node(val id: String, val x: Double, val y: Double, val z: Double)
data class Edge(val from: String, val to: String, val weight: Double, val traffic: Double)

class TrafficPredictor(private val seed: Long = 42) {
    private val rng = java.util.Random(seed)

    fun predictTrafficLoad(edge: Edge, timeStep: Int): Double {
        val base = edge.traffic
        val variation = rng.nextGaussian() * 0.1
        return (base + variation).coerceIn(0.0, 1.0)
    }

    fun predictCongestion(nodes: List<Node>, timeHorizon: Int): Map<String, Double> {
        return nodes.associate { node ->
            node.id to rng.nextDouble()
        }
    }
}

class DijkstraRouter(private val nodes: List<Node>, private val edges: List<Edge>) {

    // Dijkstra shortest path algorithm
    fun dijkstra(source: String, target: String): List<String> {
        val dist = nodes.associate { it.id to Double.MAX_VALUE }.toMutableMap()
        val prev = mutableMapOf<String, String?>()
        val visited = mutableSetOf<String>()
        dist[source] = 0.0

        while (true) {
            val u = dist.entries
                .filter { it.key !in visited }
                .minByOrNull { it.value }?.key ?: break

            if (u == target) break
            visited.add(u)

            for (edge in edges.filter { it.from == u }) {
                val alt = dist[u]!! + edge.weight
                if (alt < dist.getOrDefault(edge.to, Double.MAX_VALUE)) {
                    dist[edge.to] = alt
                    prev[edge.to] = u
                }
            }
        }

        val path = mutableListOf<String>()
        var current: String? = target
        while (current != null) {
            path.add(0, current)
            current = prev[current]
        }
        return if (path.first() == source) path else emptyList()
    }

    // Route with traffic-aware edge weights
    fun routeWithTraffic(source: String, target: String, predictor: TrafficPredictor): List<String> {
        val adjustedEdges = edges.map { e ->
            val trafficLoad = predictor.predictTrafficLoad(e, 0)
            e.copy(weight = e.weight * (1.0 + trafficLoad))
        }
        val trafficRouter = DijkstraRouter(nodes, adjustedEdges)
        return trafficRouter.dijkstra(source, target)
    }
}

// Phase 525: Predictive routing main class
class PredictiveRoutingEngine(private val numNodes: Int = 20) {
    private val rng = java.util.Random(42)
    val nodes: List<Node> = (0 until numNodes).map { i ->
        Node("N-$i", rng.nextDouble() * 1000, rng.nextDouble() * 1000, rng.nextDouble() * 100)
    }
    private val edges: List<Edge>
    val predictor = TrafficPredictor()

    init {
        val edgeList = mutableListOf<Edge>()
        for (i in nodes.indices) {
            for (j in i+1 until nodes.size) {
                val a = nodes[i]; val b = nodes[j]
                val dist = sqrt((a.x-b.x)*(a.x-b.x) + (a.y-b.y)*(a.y-b.y))
                if (dist < 300) {
                    edgeList.add(Edge(a.id, b.id, dist, rng.nextDouble() * 0.5))
                    edgeList.add(Edge(b.id, a.id, dist, rng.nextDouble() * 0.5))
                }
            }
        }
        edges = edgeList
    }

    fun route(from: String, to: String): List<String> {
        val router = DijkstraRouter(nodes, edges)
        return router.routeWithTraffic(from, to, predictor)
    }
}
