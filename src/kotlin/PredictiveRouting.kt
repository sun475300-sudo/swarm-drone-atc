// Phase 525: PredictiveRouting — Kotlin 기반 예측 경로 계획
// SDACS Predictive Routing with Traffic-Aware Dijkstra

import kotlin.math.*

// 웨이포인트 노드
data class WaypointNode(val id: Int, val lat: Double, val lon: Double, val alt: Double)

// 경로 에지 (드론 간 이동 링크)
data class RouteEdge(val from: Int, val to: Int, val distance: Double, val trafficLoad: Double)

// 교통 흐름 모델 (Traffic density map)
class TrafficModel(private val nodes: List<WaypointNode>) {
    private val trafficDensity = mutableMapOf<Pair<Int, Int>, Double>()

    fun updateTraffic(from: Int, to: Int, density: Double) {
        trafficDensity[Pair(from, to)] = density
    }

    fun getTraffic(from: Int, to: Int): Double {
        return trafficDensity.getOrDefault(Pair(from, to), 0.0)
    }

    fun trafficWeight(from: Int, to: Int, distance: Double): Double {
        val traffic = getTraffic(from, to)
        // 교통 밀도가 높을수록 가중치 증가
        return distance * (1.0 + traffic * 2.0)
    }
}

// Dijkstra 알고리즘 기반 최단 경로 탐색
class DijkstraRouter(
    private val nodes: List<WaypointNode>,
    private val edges: List<RouteEdge>,
    private val trafficModel: TrafficModel
) {
    private fun adjacency(): Map<Int, List<RouteEdge>> {
        return edges.groupBy { it.from }
    }

    // Dijkstra 최단 경로 (traffic-aware)
    fun dijkstra(startId: Int, endId: Int): List<Int>? {
        val dist = mutableMapOf<Int, Double>().withDefault { Double.MAX_VALUE }
        val prev = mutableMapOf<Int, Int?>()
        val visited = mutableSetOf<Int>()
        val adj = adjacency()

        dist[startId] = 0.0
        val queue = ArrayDeque<Int>()
        queue.add(startId)

        while (queue.isNotEmpty()) {
            // 최소 거리 노드 선택
            val current = queue.minByOrNull { dist.getValue(it) } ?: break
            queue.remove(current)
            if (current in visited) continue
            visited.add(current)
            if (current == endId) break

            for (edge in adj[current] ?: emptyList()) {
                val newDist = dist.getValue(current) + trafficModel.trafficWeight(edge.from, edge.to, edge.distance)
                if (newDist < dist.getValue(edge.to)) {
                    dist[edge.to] = newDist
                    prev[edge.to] = current
                    queue.add(edge.to)
                }
            }
        }

        // 경로 역추적
        if (dist.getValue(endId) == Double.MAX_VALUE) return null
        val path = mutableListOf<Int>()
        var cur: Int? = endId
        while (cur != null) {
            path.add(0, cur)
            cur = prev[cur]
        }
        return path
    }
}

// 예측 경로 최적화기
class PredictiveRoutePlanner(private val nodeCount: Int) {
    private val nodes: List<WaypointNode>
    private val edges: List<RouteEdge>
    private val trafficModel: TrafficModel
    private val router: DijkstraRouter

    init {
        nodes = (0 until nodeCount).map { i ->
            WaypointNode(i, 37.5 + i * 0.001, 127.0 + i * 0.001, 50.0 + i * 2.0)
        }
        edges = buildEdges()
        trafficModel = TrafficModel(nodes)
        router = DijkstraRouter(nodes, edges, trafficModel)
        initTraffic()
    }

    private fun haversine(n1: WaypointNode, n2: WaypointNode): Double {
        val r = 6371000.0
        val dLat = Math.toRadians(n2.lat - n1.lat)
        val dLon = Math.toRadians(n2.lon - n1.lon)
        val a = sin(dLat / 2).pow(2) + cos(Math.toRadians(n1.lat)) * cos(Math.toRadians(n2.lat)) * sin(dLon / 2).pow(2)
        return r * 2 * atan2(sqrt(a), sqrt(1 - a))
    }

    private fun buildEdges(): List<RouteEdge> {
        return nodes.flatMap { n1 ->
            nodes.filter { it.id != n1.id && abs(it.id - n1.id) <= 2 }.map { n2 ->
                RouteEdge(n1.id, n2.id, haversine(n1, n2), 0.0)
            }
        }
    }

    private fun initTraffic() {
        // 시뮬레이션 교통 밀도 설정
        for (i in 0 until nodeCount - 1) {
            trafficModel.updateTraffic(i, i + 1, (i % 3) * 0.3)
        }
    }

    fun planRoute(droneId: Int, startNode: Int, endNode: Int): List<Int>? {
        return router.dijkstra(startNode, endNode)
    }
}

fun main() {
    println("SDACS Predictive Routing — Phase 525\n")

    val planner = PredictiveRoutePlanner(nodeCount = 8)

    println("Dijkstra 기반 Traffic-Aware 경로 계획:")
    for (droneId in 0..2) {
        val path = planner.planRoute(droneId, 0, 7)
        if (path != null) {
            println("  드론 $droneId: ${path.joinToString(" → ")}")
        } else {
            println("  드론 $droneId: 경로 없음")
        }
    }

    println("\n예측 경로 계획 완료.")
}
