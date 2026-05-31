// SatelliteRelay.swift - Satellite relay protocol for SDACS (Phase 529)
// Swift implementation of drone-to-satellite communication with orbital handover

import Foundation
import Combine

// Satellite orbital parameters
struct OrbitalParameters {
    let altitude_km: Double      // orbital altitude
    let inclination: Double      // orbital inclination in degrees
    let period_min: Double       // orbital period in minutes
    let coverage_radius_km: Double

    var is_leo: Bool { altitude_km < 2000 }
    var angular_velocity: Double { 360.0 / period_min }
}

// Satellite node in the constellation
class SatelliteNode: Identifiable {
    let id: String
    var position: (lat: Double, lon: Double, alt: Double)
    let orbital: OrbitalParameters
    var active: Bool = true
    var load: Int = 0
    var max_connections: Int = 100

    init(id: String, lat: Double, lon: Double, orbital: OrbitalParameters) {
        self.id = id
        self.position = (lat, lon, orbital.altitude_km)
        self.orbital = orbital
    }

    func distanceTo(drone_lat: Double, drone_lon: Double) -> Double {
        let dlat = drone_lat - position.lat
        let dlon = drone_lon - position.lon
        return sqrt(dlat*dlat + dlon*dlon) * 111.0  // km
    }

    var has_capacity: Bool { load < max_connections }
}

// Handover decision record
struct HandoverDecision {
    let from_satellite: String
    let to_satellite: String
    let drone_id: String
    let timestamp: Date
    let reason: String
}

// Satellite relay manager with handover support
class SatelliteRelayManager: ObservableObject {
    @Published var satellites: [SatelliteNode] = []
    @Published var handover_count: Int = 0
    @Published var active_connections: [String: String] = [:]  // drone_id -> satellite_id

    private var handover_history: [HandoverDecision] = []

    // Find best satellite for a drone at given position
    func findBestSatellite(drone_id: String, lat: Double, lon: Double) -> SatelliteNode? {
        return satellites
            .filter { $0.active && $0.has_capacity }
            .min(by: { $0.distanceTo(drone_lat: lat, drone_lon: lon) <
                       $1.distanceTo(drone_lat: lat, drone_lon: lon) })
    }

    // Perform handover for a drone
    func performHandover(drone_id: String, lat: Double, lon: Double) -> HandoverDecision? {
        let current_sat = active_connections[drone_id]
        guard let best = findBestSatellite(drone_id: drone_id, lat: lat, lon: lon) else {
            return nil
        }

        if let current = current_sat, current == best.id { return nil }

        if let old = current_sat,
           let old_node = satellites.first(where: { $0.id == old }) {
            old_node.load -= 1
        }

        best.load += 1
        active_connections[drone_id] = best.id
        handover_count += 1

        let decision = HandoverDecision(
            from_satellite: current_sat ?? "none",
            to_satellite: best.id,
            drone_id: drone_id,
            timestamp: Date(),
            reason: "signal_optimization"
        )
        handover_history.append(decision)
        return decision
    }

    // Register a new satellite in the constellation
    func registerSatellite(_ satellite: SatelliteNode) {
        satellites.append(satellite)
    }

    var summary: [String: Any] {
        return [
            "total_satellites": satellites.count,
            "active_satellites": satellites.filter(\.active).count,
            "total_handovers": handover_count,
            "active_connections": active_connections.count
        ]
    }
}
