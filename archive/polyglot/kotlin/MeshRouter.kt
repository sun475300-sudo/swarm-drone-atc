/**
 * Phase 345: Kotlin Mesh Router
 * Dijkstra-based mesh network routing for drone swarms.
 * Sealed classes for link states, self-healing topology.
 */

package sdacs.mesh

import java.util.PriorityQueue
import kotlin.math.*

// ── Types ────────────────────────────────────────────────────────

sealed class LinkStatus {
    object Active : LinkStatus()
    object Degraded : LinkStatus()
    object Failed : LinkStatus()
}

data class MeshNode(
    val nodeId: String,
    val x: Double,
    val y: Double,
    val z: Double,
    val isGateway: Boolean = false,
    var isActive: Boolean = true,
    val neighbors: MutableSet<String> = mutableSetOf()
)

data class MeshLink(
    val src: String,
    val dst: String,
    val rssi: Double = -60.0,
    val bandwidth: Double = 10.0,
    val latency: Double = 5.0,
    var status: LinkStatus = LinkStatus.Active
) {
    val cost: Double get() = when (status) {
        is LinkStatus.Failed -> Double.MAX_VALUE
        is LinkStatus.Degraded -> (latency + 1.0 / bandwidth) * 2.0
        is LinkStatus.Active -> latency + 1.0 / bandwidth
    }
}

data class RouteEntry(
    val destination: String,
    val nextHop: String,
    val cost: Double,
    val hopCount: Int,
    val path: List<String>
)

data class NetworkStats(
    val nodes: Int,
    val activeNodes: Int,
    val gateways: Int,
    val activeLinks: Int,
    val failedLinks: Int,
    val avgCost: Double
)

// ── Mesh Router ─────────────────────────────────────────────────

class MeshRouter(private val seed: Long = 42L) {
    private val nodes = mutableMapOf<String, MeshNode>()
    private val links = mutableMapOf<Pair<String, String>, MeshLink>()
    private val routingTables = mutableMapOf<String, Map<String, RouteEntry>>()
    private val random = java.util.Random(seed)
    private var routeUpdates = 0

    fun addNode(id: String, x: Double, y: Double, z: Double,
                isGateway: Boolean = false): MeshNode {
        val node = MeshNode(id, x, y, z, isGateway)
        nodes[id] = node
        return node
    }

    fun addLink(src: String, dst: String, rssi: Double = -60.0,
                bandwidth: Double = 10.0): MeshLink {
        val a = nodes[src]!!; val b = nodes[dst]!!
        val dist = sqrt((a.x - b.x).pow(2) + (a.y - b.y).pow(2) + (a.z - b.z).pow(2))
        val latency = dist / 300.0 + 1.0

        val link = MeshLink(src, dst, rssi, bandwidth, latency)
        links[src to dst] = link
        links[dst to src] = MeshLink(dst, src, rssi, bandwidth, latency)
        a.neighbors.add(dst)
        b.neighbors.add(src)
        return link
    }

    fun autoConnect(maxRange: Double = 200.0): Int {
        var count = 0
        val ids = nodes.keys.toList()
        for (i in ids.indices) {
            for (j in i + 1 until ids.size) {
                val a = nodes[ids[i]]!!; val b = nodes[ids[j]]!!
                val dist = sqrt((a.x - b.x).pow(2) + (a.y - b.y).pow(2) + (a.z - b.z).pow(2))
                if (dist <= maxRange) {
                    val rssi = -30.0 - 20 * log10(maxOf(dist, 1.0))
                    val bw = maxOf(1.0, 54.0 * (1.0 - dist / maxRange))
                    addLink(ids[i], ids[j], rssi, bw)
                    count++
                }
            }
        }
        return count
    }

    fun computeRoutes(source: String? = null) {
        val sources = if (source != null) listOf(source) else nodes.keys.toList()
        for (src in sources) {
            routingTables[src] = dijkstra(src)
            routeUpdates++
        }
    }

    private fun dijkstra(source: String): Map<String, RouteEntry> {
        val dist = mutableMapOf<String, Double>()
        val prev = mutableMapOf<String, String?>()
        nodes.keys.forEach { dist[it] = Double.MAX_VALUE; prev[it] = null }
        dist[source] = 0.0

        val pq = PriorityQueue<Pair<Double, String>>(compareBy { it.first })
        pq.add(0.0 to source)
        val visited = mutableSetOf<String>()

        while (pq.isNotEmpty()) {
            val (d, u) = pq.poll()
            if (u in visited) continue
            visited.add(u)
            val node = nodes[u] ?: continue
            if (!node.isActive) continue

            for (neighbor in node.neighbors) {
                val link = links[u to neighbor] ?: continue
                if (link.status is LinkStatus.Failed) continue
                val alt = d + link.cost
                if (alt < (dist[neighbor] ?: Double.MAX_VALUE)) {
                    dist[neighbor] = alt
                    prev[neighbor] = u
                    pq.add(alt to neighbor)
                }
            }
        }

        val routes = mutableMapOf<String, RouteEntry>()
        for (dst in nodes.keys) {
            if (dst == source || dist[dst] == Double.MAX_VALUE) continue
            val path = mutableListOf<String>()
            var node: String? = dst
            while (node != null) { path.add(node); node = prev[node] }
            path.reverse()
            val nextHop = if (path.size > 1) path[1] else dst
            routes[dst] = RouteEntry(dst, nextHop, dist[dst]!!, path.size - 1, path)
        }
        return routes
    }

    fun getRoute(src: String, dst: String): RouteEntry? =
        routingTables[src]?.get(dst)

    fun failLink(src: String, dst: String) {
        links[src to dst]?.status = LinkStatus.Failed
        links[dst to src]?.status = LinkStatus.Failed
    }

    fun failNode(nodeId: String) {
        nodes[nodeId]?.isActive = false
        nodes[nodeId]?.neighbors?.forEach { failLink(nodeId, it) }
    }

    fun stats(): NetworkStats {
        val active = links.values.count { it.status is LinkStatus.Active }
        val failed = links.values.count { it.status is LinkStatus.Failed }
        val costs = links.values.filter { it.status !is LinkStatus.Failed }.map { it.cost }
        return NetworkStats(
            nodes = nodes.size,
            activeNodes = nodes.values.count { it.isActive },
            gateways = nodes.values.count { it.isGateway },
            activeLinks = active / 2,
            failedLinks = failed / 2,
            avgCost = if (costs.isNotEmpty()) costs.average() else 0.0
        )
    }
}

// ── Main ────────────────────────────────────────────────────────

fun main() {
    val router = MeshRouter(42)

    for (i in 0 until 8) {
        val angle = 2 * PI * i / 8
        router.addNode("drone_$i", cos(angle) * 100, sin(angle) * 100, 50.0,
            isGateway = (i == 0))
    }
    router.autoConnect(150.0)
    router.computeRoutes()

    val route = router.getRoute("drone_0", "drone_4")
    if (route != null) {
        println("Route: ${route.path} cost=${String.format("%.2f", route.cost)} hops=${route.hopCount}")
    }

    router.failNode("drone_2")
    router.computeRoutes()
    val route2 = router.getRoute("drone_0", "drone_4")
    println("After failure: ${route2?.path ?: "no route"}")
    println("Stats: ${router.stats()}")
}
