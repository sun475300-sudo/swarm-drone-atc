// SDACS Predictive Routing — Kotlin (Phase 525)
// 드론 군집 예측적 경로계획 (Dijkstra + 교통량 예측)

package sdacs.routing

import kotlin.math.sqrt
import kotlin.math.pow
import java.util.PriorityQueue

data class Waypoint(val id: String, val x: Double, val y: Double, val z: Double) {
    fun distanceTo(other: Waypoint): Double =
        sqrt((x - other.x).pow(2) + (y - other.y).pow(2) + (z - other.z).pow(2))
}

data class Edge(val from: String, val to: String, val weight: Double)

// Phase 525 — 교통량(Traffic) 예측 모델
class TrafficModel {
    private val congestion = mutableMapOf<String, Double>()

    fun update(edgeId: String, trafficLoad: Double) {
        congestion[edgeId] = trafficLoad.coerceIn(0.0, 1.0)
    }

    fun getWeight(from: String, to: String, baseWeight: Double): Double {
        val key = "$from->$to"
        val load = congestion.getOrDefault(key, 0.0)
        return baseWeight * (1.0 + load * 2.0)  // 교통량 가중치 반영
    }

    fun predictCongestion(edgeId: String, timeHorizon: Double): Double {
        val current = congestion.getOrDefault(edgeId, 0.0)
        return (current * (1.0 - timeHorizon / 60.0)).coerceAtLeast(0.0)
    }
}

// Dijkstra 최단 경로
class PredictiveRouter(private val trafficModel: TrafficModel) {

    fun dijkstra(
        waypoints: Map<String, Waypoint>,
        edges: List<Edge>,
        source: String,
        target: String
    ): List<String> {
        val dist = mutableMapOf<String, Double>().withDefault { Double.MAX_VALUE }
        val prev = mutableMapOf<String, String?>()
        val pq = PriorityQueue<Pair<Double, String>>(compareBy { it.first })

        dist[source] = 0.0
        pq.add(Pair(0.0, source))

        val adjacency = buildMap<String, MutableList<Edge>> {
            for (e in edges) getOrPut(e.from) { mutableListOf() }.add(e)
        }

        while (pq.isNotEmpty()) {
            val (d, u) = pq.poll()
            if (d > (dist[u] ?: Double.MAX_VALUE)) continue
            if (u == target) break

            for (edge in adjacency[u] ?: emptyList()) {
                val w = trafficModel.getWeight(edge.from, edge.to, edge.weight)
                val newDist = d + w
                if (newDist < (dist[edge.to] ?: Double.MAX_VALUE)) {
                    dist[edge.to] = newDist
                    prev[edge.to] = u
                    pq.add(Pair(newDist, edge.to))
                }
            }
        }

        return reconstructPath(prev, source, target)
    }

    private fun reconstructPath(prev: Map<String, String?>, source: String, target: String): List<String> {
        val path = mutableListOf<String>()
        var cur: String? = target
        while (cur != null) {
            path.add(0, cur)
            cur = prev[cur]
        }
        return if (path.firstOrNull() == source) path else emptyList()
    }

    fun planFleetRoutes(
        fleet: Map<String, Pair<String, String>>,  // droneId -> (source, target)
        waypoints: Map<String, Waypoint>,
        edges: List<Edge>
    ): Map<String, List<String>> {
        return fleet.mapValues { (_, srcTgt) ->
            dijkstra(waypoints, edges, srcTgt.first, srcTgt.second)
        }
    }
}

// 충돌 회피를 위한 경로 분리
object RouteDeconflict {
    fun separateRoutes(routes: Map<String, List<String>>): Map<String, List<String>> {
        val used = mutableSetOf<String>()
        return routes.mapValues { (_, path) ->
            path.filterNot { wp ->
                val conflict = wp in used
                used.add(wp)
                conflict
            }
        }
    }
}
