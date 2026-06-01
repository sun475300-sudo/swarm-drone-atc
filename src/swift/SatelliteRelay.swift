// Phase 529 — Satellite Relay with Orbital Parameters and Handover Logic
// Swift module for managing satellite communication relay in drone swarm operations.

import Foundation

// MARK: - Types and Structures

/// Orbital parameters for a communications satellite
struct OrbitalParameters {
    let altitude: Double        // km above Earth
    let inclination: Double     // degrees
    let eccentricity: Double    // 0.0 = circular
    let period: Double          // minutes
    let raan: Double            // Right Ascension of Ascending Node, degrees

    /// Compute approximate ground speed (km/s)
    var groundSpeed: Double {
        let earthRadius = 6371.0
        let orbitalRadius = earthRadius + altitude
        let mu = 398600.4418  // Earth's gravitational parameter km^3/s^2
        return (mu / orbitalRadius).squareRoot()
    }
}

/// A single Satellite node in the relay network
class Satellite {
    let id: String
    let name: String
    var orbital: OrbitalParameters
    var isActive: Bool
    var signalStrength: Double   // dBm
    var connectedDrones: [String]

    init(id: String, name: String, orbital: OrbitalParameters) {
        self.id = id
        self.name = name
        self.orbital = orbital
        self.isActive = true
        self.signalStrength = -70.0
        self.connectedDrones = []
    }

    /// Check if satellite is in range for a given ground position
    func isInRange(latitude: Double, longitude: Double) -> Bool {
        // Simplified visibility: satellites with altitude > 500km cover ~30% of Earth per pass
        let coverageAngle = atan(orbital.altitude / 6371.0) * 180.0 / Double.pi
        return coverageAngle > 10.0 && isActive  // simplified check
    }

    /// Compute link budget (simplified Friis equation stub)
    func linkBudget(distanceKm: Double) -> Double {
        let transmitPower = 30.0  // dBm
        let pathLoss = 20.0 * log10(distanceKm * 1000.0) + 20.0 * log10(2.4e9) - 147.55
        return transmitPower - pathLoss
    }
}

// MARK: - Handover Logic

/// Handover trigger conditions
enum HandoverReason: String {
    case signalDegradation = "SIGNAL_DEGRADATION"
    case orbitalTransition  = "ORBITAL_TRANSITION"
    case loadBalancing      = "LOAD_BALANCING"
    case satelliteFault     = "SATELLITE_FAULT"
}

/// Result of a handover decision
struct HandoverDecision {
    let droneId: String
    let fromSatellite: String
    let toSatellite: String
    let reason: HandoverReason
    let timestamp: Date
    let successful: Bool
}

/// Satellite handover manager for the drone swarm relay network
class SatelliteHandoverManager {
    private var satellites: [String: Satellite] = [:]
    private var droneAssignments: [String: String] = [:]  // droneId -> satelliteId
    private var handoverHistory: [HandoverDecision] = []

    func registerSatellite(_ satellite: Satellite) {
        satellites[satellite.id] = satellite
    }

    /// Assign a drone to the best available satellite
    func assignDrone(droneId: String, latitude: Double, longitude: Double) -> String? {
        let available = satellites.values.filter { $0.isInRange(latitude: latitude, longitude: longitude) }
        guard let best = available.max(by: { $0.signalStrength < $1.signalStrength }) else {
            return nil
        }
        droneAssignments[droneId] = best.id
        best.connectedDrones.append(droneId)
        return best.id
    }

    /// Evaluate and perform handover if necessary
    func evaluateHandover(droneId: String, currentSignal: Double, latitude: Double, longitude: Double) -> HandoverDecision? {
        guard let currentSatId = droneAssignments[droneId],
              let currentSat = satellites[currentSatId] else { return nil }

        // Check if handover is needed
        guard currentSignal < -85.0 else { return nil }

        // Find better satellite
        let candidates = satellites.values.filter {
            $0.id != currentSatId && $0.isInRange(latitude: latitude, longitude: longitude)
        }
        guard let target = candidates.max(by: { $0.signalStrength < $1.signalStrength }) else {
            return nil
        }

        // Perform handover
        currentSat.connectedDrones.removeAll { $0 == droneId }
        target.connectedDrones.append(droneId)
        droneAssignments[droneId] = target.id

        let decision = HandoverDecision(
            droneId: droneId,
            fromSatellite: currentSatId,
            toSatellite: target.id,
            reason: .signalDegradation,
            timestamp: Date(),
            successful: true
        )
        handoverHistory.append(decision)
        return decision
    }

    /// Get handover statistics
    func handoverStats() -> [String: Any] {
        let successful = handoverHistory.filter { $0.successful }.count
        return [
            "total_handovers": handoverHistory.count,
            "successful": successful,
            "satellites": satellites.count,
            "connected_drones": droneAssignments.count
        ]
    }
}

// MARK: - Relay Network

/// The complete satellite relay network for swarm communications
class SatelliteRelayNetwork {
    let networkId: String
    var handoverManager: SatelliteHandoverManager
    var telemetryBuffer: [(droneId: String, data: [String: Double])] = []

    init(networkId: String) {
        self.networkId = networkId
        self.handoverManager = SatelliteHandoverManager()
        setupDefaultConstellation()
    }

    private func setupDefaultConstellation() {
        // Low Earth Orbit satellites
        let leo1 = Satellite(id: "SAT-001", name: "LEO-Alpha",
                             orbital: OrbitalParameters(altitude: 550, inclination: 53, eccentricity: 0.001, period: 95.5, raan: 0))
        let leo2 = Satellite(id: "SAT-002", name: "LEO-Beta",
                             orbital: OrbitalParameters(altitude: 560, inclination: 53, eccentricity: 0.001, period: 96.0, raan: 60))
        let geo1 = Satellite(id: "SAT-GEO", name: "GEO-Relay",
                             orbital: OrbitalParameters(altitude: 35786, inclination: 0, eccentricity: 0.0, period: 1436.0, raan: 0))
        handoverManager.registerSatellite(leo1)
        handoverManager.registerSatellite(leo2)
        handoverManager.registerSatellite(geo1)
    }

    func relayTelemetry(droneId: String, data: [String: Double]) {
        telemetryBuffer.append((droneId: droneId, data: data))
    }

    func status() -> String {
        let stats = handoverManager.handoverStats()
        return "Phase 529 SatelliteRelay[\(networkId)] | Handovers: \(stats["total_handovers"] ?? 0) | Satellites: \(stats["satellites"] ?? 0)"
    }
}

// MARK: - Main
let network = SatelliteRelayNetwork(networkId: "SWARM-NET-01")
let _ = network.handoverManager.assignDrone(droneId: "D001", latitude: 37.5, longitude: 127.0)
let _ = network.handoverManager.evaluateHandover(droneId: "D001", currentSignal: -90.0, latitude: 37.6, longitude: 127.1)
print(network.status())
