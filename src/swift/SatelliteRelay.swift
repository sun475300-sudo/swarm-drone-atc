// Phase 529 — Satellite relay protocol for drone comms.
// Orbital slot tracking, handover procedure, and link budget estimation.
// Designed for BVLOS (beyond visual line-of-sight) swarm operations.

import Foundation

// ---- Phase marker ----
let PHASE_MARKER: Int = 529

// ---- Orbital slot definition ----
/// Represents a single Satellite in a LEO relay constellation.
struct SatelliteSlot: Identifiable {
    let id: String
    let orbitalAltitudeKm: Double      // orbital altitude above Earth's surface
    let inclinationDeg: Double          // orbital inclination in degrees
    var longitudeDeg: Double            // current sub-satellite point longitude
    var latitudeDeg: Double             // current sub-satellite point latitude
    var isVisible: Bool                 // visibility from a given ground point

    /// Estimated free-space path loss in dB for this orbital altitude and frequency.
    func pathLossDB(frequencyMHz: Double) -> Double {
        let distanceKm = orbitalAltitudeKm
        // FSPL(dB) = 20*log10(d_km * 1000) + 20*log10(f_Hz) - 147.55
        let fHz = frequencyMHz * 1_000_000.0
        return 20.0 * log10(distanceKm * 1000.0) + 20.0 * log10(fHz) - 147.55
    }
}

// ---- Constellation manager ----
/// Tracks a fleet of Satellite slots and provides visibility queries.
final class ConstellationManager {
    private(set) var slots: [SatelliteSlot]

    init(slots: [SatelliteSlot]) {
        self.slots = slots
    }

    /// Returns all Satellite slots currently visible from [lat, lon] within [elevationMaskDeg].
    func visibleSlots(fromLat lat: Double, lon: Double, elevationMaskDeg: Double = 5.0) -> [SatelliteSlot] {
        // Simplified visibility: Satellite is visible if its sub-point is within
        // Earth central angle corresponding to the elevation mask and orbital altitude.
        return slots.filter { slot in
            let centralAngle = centralAngleDeg(
                fromLat: lat, fromLon: lon,
                toLat: slot.latitudeDeg, toLon: slot.longitudeDeg
            )
            let earthRadiusKm = 6371.0
            let maxCentralAngleDeg = acos(earthRadiusKm / (earthRadiusKm + slot.orbitalAltitudeKm)) * 180.0 / .pi
            return centralAngle < maxCentralAngleDeg - elevationMaskDeg
        }
    }

    /// Update orbital positions for a simulated elapsed time step.
    /// Simplified: advance longitude by angular rate proportional to orbital period.
    func tick(deltaSeconds: Double) {
        for i in slots.indices {
            let earthRadiusKm = 6371.0
            let mu = 398600.4418  // km^3/s^2 gravitational parameter
            let r = earthRadiusKm + slots[i].orbitalAltitudeKm
            let period = 2.0 * .pi * sqrt(pow(r, 3) / mu)  // seconds
            let angularRateDegPerSec = 360.0 / period
            slots[i].longitudeDeg += angularRateDegPerSec * deltaSeconds
            // Wrap longitude to [-180, 180]
            if slots[i].longitudeDeg > 180.0  { slots[i].longitudeDeg -= 360.0 }
            if slots[i].longitudeDeg < -180.0 { slots[i].longitudeDeg += 360.0 }
        }
    }

    private func centralAngleDeg(fromLat lat1: Double, fromLon lon1: Double,
                                  toLat lat2: Double, toLon lon2: Double) -> Double {
        let phi1 = lat1 * .pi / 180.0
        let phi2 = lat2 * .pi / 180.0
        let dLon = (lon2 - lon1) * .pi / 180.0
        let cosAngle = sin(phi1) * sin(phi2) + cos(phi1) * cos(phi2) * cos(dLon)
        return acos(max(-1.0, min(1.0, cosAngle))) * 180.0 / .pi
    }
}

// ---- Handover state machine ----
/// States in the Satellite link handover FSM.
enum HandoverState: String {
    case idle          = "IDLE"
    case scanning      = "SCANNING"           // searching for new Satellite
    case negotiating   = "NEGOTIATING"        // beamforming + auth
    case switchingLink = "SWITCHING_LINK"     // traffic migrating
    case committed     = "COMMITTED"          // handover complete
    case failed        = "FAILED"
}

/// Manages the handover procedure between two Satellite slots.
final class HandoverController {
    private(set) var state: HandoverState = .idle
    private(set) var activeSatellite: SatelliteSlot?
    private(set) var candidateSatellite: SatelliteSlot?
    private let signalThresholdDB: Double

    init(signalThresholdDB: Double = -120.0) {
        self.signalThresholdDB = signalThresholdDB
    }

    /// Evaluate whether a handover is needed given current signal quality.
    func evaluate(constellation: ConstellationManager, droneLatitude: Double, droneLongitude: Double) {
        let visible = constellation.visibleSlots(fromLat: droneLatitude, lon: droneLongitude)
        guard !visible.isEmpty else {
            state = .failed
            print("[Phase \(PHASE_MARKER)] handover: no visible satellites — link lost")
            return
        }
        // Pick best satellite by lowest path loss
        let best = visible.min(by: { $0.pathLossDB(frequencyMHz: 2000.0) < $1.pathLossDB(frequencyMHz: 2000.0) })!
        if activeSatellite == nil {
            activate(best)
            return
        }
        // Trigger handover if active link degrades below threshold
        let activePathLoss = activeSatellite!.pathLossDB(frequencyMHz: 2000.0)
        if -activePathLoss < signalThresholdDB {
            beginHandover(to: best)
        }
    }

    private func activate(_ slot: SatelliteSlot) {
        activeSatellite = slot
        state = .committed
        print("[Phase \(PHASE_MARKER)] Link activated via Satellite \(slot.id) @ \(slot.orbitalAltitudeKm) km")
    }

    /// Execute the handover sequence to a new Satellite slot.
    func beginHandover(to candidate: SatelliteSlot) {
        state = .scanning
        candidateSatellite = candidate
        print("[Phase \(PHASE_MARKER)] handover initiated: \(activeSatellite?.id ?? "none") → \(candidate.id)")
        state = .negotiating
        // Simulate negotiation delay (would be async in production)
        state = .switchingLink
        activeSatellite = candidate
        candidateSatellite = nil
        state = .committed
        print("[Phase \(PHASE_MARKER)] handover complete: now on \(candidate.id)")
    }

    var isLinked: Bool { state == .committed }
}

// ---- Link budget calculator ----
/// Computes end-to-end link budget for a drone↔Satellite↔ground path.
struct LinkBudget {
    let txPowerDBm: Double
    let txGainDB: Double
    let rxGainDB: Double
    let systemNoiseDB: Double
    let requiredEbN0DB: Double

    func marginDB(pathLossDB: Double) -> Double {
        return txPowerDBm + txGainDB + rxGainDB - pathLossDB - systemNoiseDB - requiredEbN0DB
    }
}

// ---- Smoke test ----
func runSmokeTest() {
    print("[Phase \(PHASE_MARKER)] SatelliteRelay smoke test")

    let slots: [SatelliteSlot] = [
        SatelliteSlot(id: "SAT-01", orbitalAltitudeKm: 550, inclinationDeg: 53.0,
                      longitudeDeg: 10.0, latitudeDeg: 37.5, isVisible: true),
        SatelliteSlot(id: "SAT-02", orbitalAltitudeKm: 550, inclinationDeg: 53.0,
                      longitudeDeg: 45.0, latitudeDeg: 35.0, isVisible: true),
        SatelliteSlot(id: "SAT-03", orbitalAltitudeKm: 1200, inclinationDeg: 86.4,
                      longitudeDeg: -30.0, latitudeDeg: 40.0, isVisible: false),
    ]

    let constellation = ConstellationManager(slots: slots)
    let controller = HandoverController(signalThresholdDB: -105.0)

    controller.evaluate(constellation: constellation, droneLatitude: 37.5, droneLongitude: 127.0)
    constellation.tick(deltaSeconds: 60.0)
    controller.evaluate(constellation: constellation, droneLatitude: 37.6, droneLongitude: 127.1)

    let budget = LinkBudget(txPowerDBm: 30.0, txGainDB: 6.0, rxGainDB: 4.0,
                            systemNoiseDB: 5.0, requiredEbN0DB: 10.0)
    let pl = slots[0].pathLossDB(frequencyMHz: 2000.0)
    let margin = budget.marginDB(pathLossDB: pl)
    print("[Phase \(PHASE_MARKER)] path_loss=\(String(format: "%.1f", pl)) dB  margin=\(String(format: "%.1f", margin)) dB")
    print("[Phase \(PHASE_MARKER)] linked=\(controller.isLinked)  active=\(controller.activeSatellite?.id ?? "none")")
    print("[Phase \(PHASE_MARKER)] done.")
}

runSmokeTest()
