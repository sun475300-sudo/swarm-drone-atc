// Phase 525 — Predictive routing using Dijkstra with traffic-aware cost model
// for drone airspace. Integrates historical traffic density maps and congestion
// forecasts to produce minimum-cost paths through the airspace grid.

package sdacs.routing

import java.util.PriorityQueue

// Phase identifier
const val PHASE_MARKER = 525

// ---- Airspace grid cell ----

/** 3D airspace cell addressed by (x, y, z) integer coordinates. */
data class GridCell(val x: Int, val y: Int, val z: Int)

/** Edge in the airspace navigation graph, connecting two adjacent cells. */
data class Edge(val to: GridCell, val baseCost: Double)

// ---- Traffic model ----

/**
 * TrafficLayer holds predicted traffic density per cell per time bucket.
 * density is in [0.0, 1.0]: 0 = empty, 1 = maximum drone density.
 * Used by the cost model to inflate edge weights when congestion is high.
 */
class TrafficLayer(
    private val density: Map<GridCell, Double> = emptyMap(),
    val timeBucketSeconds: Int = 10
) {
    /** Return predicted traffic density at a cell (defaults to 0.0 if unknown). */
    fun densityAt(cell: GridCell): Double = density.getOrDefault(cell, 0.0)

    /** Traffic-aware cost multiplier: congested cells incur up to 5x base cost. */
    fun costMultiplier(cell: GridCell): Double {
        val d = densityAt(cell).coerceIn(0.0, 1.0)
        return 1.0 + 4.0 * d  // linear scale: 1x (empty) to 5x (full)
    }
}

// ---- Airspace navigation graph ----

/**
 * AirspaceGraph models the airspace as a directed weighted graph.
 * Edges are 3D grid adjacencies (26-connectivity including diagonals).
 */
class AirspaceGraph {
    private val adjacency = mutableMapOf<GridCell, MutableList<Edge>>()

    /** Register a directed edge. */
    fun addEdge(from: GridCell, edge: Edge) {
        adjacency.getOrPut(from) { mutableListOf() }.add(edge)
    }

    /** Add bidirectional edge with uniform base cost. */
    fun addUndirectedEdge(a: GridCell, b: GridCell, cost: Double = 1.0) {
        addEdge(a, Edge(to = b, baseCost = cost))
        addEdge(b, Edge(to = a, baseCost = cost))
    }

    fun neighbors(cell: GridCell): List<Edge> = adjacency[cell] ?: emptyList()

    fun allCells(): Set<GridCell> = adjacency.keys.toSet()
}

// ---- Dijkstra result ----

/** Result of a single Dijkstra run. */
data class RoutingResult(
    val path: List<GridCell>,      // ordered from source to destination
    val totalCost: Double,         // sum of traffic-aware edge costs
    val reachable: Boolean         // false if destination was unreachable
)

// ---- Traffic-aware Dijkstra implementation ----

/**
 * PredictiveRouter computes minimum-cost routes through the airspace,
 * weighting edges by base distance plus forecasted traffic congestion.
 *
 * Phase 525: Dijkstra + traffic density cost model.
 */
class PredictiveRouter(
    private val graph: AirspaceGraph,
    private val traffic: TrafficLayer = TrafficLayer()
) {
    private data class State(val cell: GridCell, val cost: Double) : Comparable<State> {
        override fun compareTo(other: State) = cost.compareTo(other.cost)
    }

    /**
     * Run Dijkstra from [source] to [destination].
     * Edge cost = baseCost * trafficMultiplier(destinationCell).
     */
    fun route(source: GridCell, destination: GridCell): RoutingResult {
        if (source == destination) {
            return RoutingResult(listOf(source), 0.0, true)
        }

        val dist = mutableMapOf<GridCell, Double>().withDefault { Double.MAX_VALUE }
        val prev = mutableMapOf<GridCell, GridCell?>()
        val pq = PriorityQueue<State>()

        dist[source] = 0.0
        pq.add(State(source, 0.0))

        while (pq.isNotEmpty()) {
            val (current, currentCost) = pq.poll()
            if (currentCost > dist.getValue(current)) continue
            if (current == destination) break

            for (edge in graph.neighbors(current)) {
                val edgeCost = edge.baseCost * traffic.costMultiplier(edge.to)
                val newCost = currentCost + edgeCost
                if (newCost < dist.getValue(edge.to)) {
                    dist[edge.to] = newCost
                    prev[edge.to] = current
                    pq.add(State(edge.to, newCost))
                }
            }
        }

        val totalCost = dist.getValue(destination)
        if (totalCost == Double.MAX_VALUE) {
            return RoutingResult(emptyList(), Double.MAX_VALUE, false)
        }

        val path = reconstructPath(prev, source, destination)
        return RoutingResult(path, totalCost, true)
    }

    private fun reconstructPath(
        prev: Map<GridCell, GridCell?>,
        source: GridCell,
        destination: GridCell
    ): List<GridCell> {
        val path = mutableListOf<GridCell>()
        var cur: GridCell? = destination
        while (cur != null) {
            path.add(0, cur)
            cur = prev[cur]
        }
        return if (path.firstOrNull() == source) path else emptyList()
    }

    /**
     * Batch route computation: finds paths from one source to multiple destinations.
     * Runs a single Dijkstra pass and extracts all paths from the SPT.
     */
    fun routeMulti(source: GridCell, destinations: Set<GridCell>): Map<GridCell, RoutingResult> {
        val dist = mutableMapOf<GridCell, Double>().withDefault { Double.MAX_VALUE }
        val prev = mutableMapOf<GridCell, GridCell?>()
        val pq = PriorityQueue<State>()
        val remaining = destinations.toMutableSet()

        dist[source] = 0.0
        pq.add(State(source, 0.0))

        while (pq.isNotEmpty() && remaining.isNotEmpty()) {
            val (current, currentCost) = pq.poll()
            if (currentCost > dist.getValue(current)) continue
            remaining.remove(current)

            for (edge in graph.neighbors(current)) {
                val edgeCost = edge.baseCost * traffic.costMultiplier(edge.to)
                val newCost = currentCost + edgeCost
                if (newCost < dist.getValue(edge.to)) {
                    dist[edge.to] = newCost
                    prev[edge.to] = current
                    pq.add(State(edge.to, newCost))
                }
            }
        }

        return destinations.associateWith { dest ->
            val cost = dist.getValue(dest)
            if (cost == Double.MAX_VALUE) {
                RoutingResult(emptyList(), Double.MAX_VALUE, false)
            } else {
                RoutingResult(reconstructPath(prev, source, dest), cost, true)
            }
        }
    }
}

// ---- Convenience factory for building a uniform 3D airspace grid ----

/**
 * Build a fully connected 3D grid graph of size [xMax] x [yMax] x [zMax].
 * Each cell is connected to its face-adjacent neighbours (6-connectivity).
 */
fun buildGridGraph(xMax: Int, yMax: Int, zMax: Int): AirspaceGraph {
    val graph = AirspaceGraph()
    val deltas = listOf(
        Triple(1, 0, 0), Triple(-1, 0, 0),
        Triple(0, 1, 0), Triple(0, -1, 0),
        Triple(0, 0, 1), Triple(0, 0, -1)
    )
    for (x in 0 until xMax) for (y in 0 until yMax) for (z in 0 until zMax) {
        val cell = GridCell(x, y, z)
        for ((dx, dy, dz) in deltas) {
            val nx = x + dx; val ny = y + dy; val nz = z + dz
            if (nx in 0 until xMax && ny in 0 until yMax && nz in 0 until zMax) {
                graph.addEdge(cell, Edge(to = GridCell(nx, ny, nz), baseCost = 1.0))
            }
        }
    }
    return graph
}
