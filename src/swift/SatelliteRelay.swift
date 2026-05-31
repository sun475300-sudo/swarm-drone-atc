// P529: SatelliteRelay - Swift satellite communication relay for drones
// Phase 529: Orbital satellite link management with handover protocols

import Foundation

// Satellite orbital parameters
struct OrbitalParams {
    let altitude_km: Double         // orbital altitude
    let inclination_deg: Double     // inclination angle
    let period_min: Double          // orbital period in minutes
    let elevation_threshold_deg: Double = 5.0  // min elevation for link
}

// Satellite state
struct SatelliteState {
    let id: String
    var elevation_deg: Double       // current elevation angle
    var azimuth_deg: Double
    var signal_strength_dbm: Double
    var isVisible: Bool
    var linkQuality: Double         // 0..1

    init(id: String, elevation: Double, azimuth: Double, signal: Double) {
        self.id = id
        self.elevation_deg = elevation
        self.azimuth_deg = azimuth
        self.signal_strength_dbm = signal
        self.isVisible = elevation > 5.0
        self.linkQuality = isVisible ? min(1.0, (elevation - 5.0) / 85.0) : 0.0
    }
}

// Handover event types
enum HandoverType {
    case satelliteHandover(from: String, to: String)
    case linkEstablished(satelliteId: String)
    case linkLost(satelliteId: String)
    case qualityDegraded(satelliteId: String, quality: Double)
}

// Satellite relay manager
class SatelliteRelay {
    private var satellites: [String: SatelliteState] = [:]
    private var activeSatellite: String?
    private var handoverHistory: [HandoverEvent] = []
    private let handoverThreshold: Double = 0.3

    struct HandoverEvent {
        let timestamp: Date
        let type: HandoverType
        let droneId: String
    }

    func registerSatellite(_ state: SatelliteState) {
        satellites[state.id] = state
    }

    func updateSatellite(id: String, elevation: Double, azimuth: Double, signal: Double) {
        satellites[id] = SatelliteState(id: id, elevation: elevation,
                                         azimuth: azimuth, signal: signal)
        checkHandover(for: id)
    }

    // Handover algorithm: switch to best visible Satellite
    private func checkHandover(for updatedId: String) {
        guard let current = activeSatellite,
              let currentState = satellites[current] else {
            initiateHandover(to: bestSatellite())
            return
        }

        if currentState.linkQuality < handoverThreshold {
            if let best = bestSatellite(), best != current {
                initiateHandover(to: best)
            }
        }
    }

    private func bestSatellite() -> String? {
        satellites.values
            .filter { $0.isVisible }
            .max(by: { $0.linkQuality < $1.linkQuality })
            .map { $0.id }
    }

    private func initiateHandover(to newSatId: String?) {
        guard let newId = newSatId else { return }
        let event: HandoverType
        if let old = activeSatellite {
            event = .satelliteHandover(from: old, to: newId)
        } else {
            event = .linkEstablished(satelliteId: newId)
        }
        handoverHistory.append(HandoverEvent(timestamp: Date(), type: event, droneId: "local"))
        activeSatellite = newId
    }

    var activeLink: SatelliteState? {
        guard let id = activeSatellite else { return nil }
        return satellites[id]
    }

    var handoverCount: Int { handoverHistory.count }
}
