// Phase 529: Satellite Relay — 드론-위성 릴레이 통신 (Swift)
// Orbital satellite relay system for beyond-LOS drone swarm communication.
import Foundation

let PHASE = 529

// ── Orbital mechanics ─────────────────────────────────────────────

struct OrbitalParameters {
    let altitude: Double      // km
    let inclination: Double   // degrees
    let period: Double        // minutes
    let coverage_radius: Double  // km on ground

    static let leo = OrbitalParameters(
        altitude: 550.0,
        inclination: 53.0,
        period: 95.5,
        coverage_radius: 2600.0
    )
}

// ── Satellite node ─────────────────────────────────────────────────

class SatelliteNode {
    let id: Int
    let orbit: OrbitalParameters
    var x: Double
    var y: Double
    var active: Bool
    var handover_pending: Bool

    init(id: Int, orbit: OrbitalParameters) {
        self.id = id
        self.orbit = orbit
        self.x = Double(id) * 1200.0
        self.y = orbit.altitude
        self.active = true
        self.handover_pending = false
    }

    /// Update satellite position (simplified great-circle arc).
    func advance(dt: Double) {
        let angular_speed = 360.0 / (orbit.period * 60.0)  // deg/s
        x += angular_speed * dt * 110.0  // approx km/deg
    }

    /// Check if a ground point is within coverage.
    func inCoverage(groundX: Double, groundY: Double) -> Bool {
        let dist = sqrt(pow(groundX - x, 2) + pow(groundY, 2))
        return dist < orbit.coverage_radius
    }
}

// ── Handover manager ─────────────────────────────────────────────

class HandoverManager {
    var satellites: [SatelliteNode]
    var handovers: [(from: Int, to: Int, time: Double)]

    init(satellites: [SatelliteNode]) {
        self.satellites = satellites
        self.handovers = []
    }

    /// Execute handover from satellite to best available.
    func handover(drone_x: Double, drone_y: Double, current_sat: Int, time: Double) -> Int {
        let best = satellites.filter { $0.active && $0.id != current_sat }
                             .max { $0.inCoverage(groundX: drone_x, groundY: drone_y) ? 0 : 1 }
        guard let new_sat = best else { return current_sat }
        if new_sat.inCoverage(groundX: drone_x, groundY: drone_y) {
            handovers.append((from: current_sat, to: new_sat.id, time: time))
            return new_sat.id
        }
        return current_sat
    }
}

// ── Satellite Relay System ─────────────────────────────────────────

class SatelliteRelay {
    let satellites: [SatelliteNode]
    let handoverMgr: HandoverManager
    var time: Double
    var messages_relayed: Int
    var handover_count: Int { handoverMgr.handovers.count }

    init(nSatellites: Int) {
        let sats = (0..<nSatellites).map { SatelliteNode(id: $0, orbit: .leo) }
        self.satellites = sats
        self.handoverMgr = HandoverManager(satellites: sats)
        self.time = 0.0
        self.messages_relayed = 0
    }

    func step(dt: Double) {
        time += dt
        satellites.forEach { $0.advance(dt: dt) }
        messages_relayed += satellites.filter { $0.active }.count
    }

    func run(steps: Int, dt: Double = 1.0) {
        for _ in 0..<steps { step(dt: dt) }
    }

    func summary() -> [String: Any] {
        return [
            "phase": PHASE,
            "satellites": satellites.count,
            "time_s": time,
            "messages_relayed": messages_relayed,
            "handover_count": handover_count,
            "orbital_altitude_km": OrbitalParameters.leo.altitude
        ]
    }
}

// ── Entry point ────────────────────────────────────────────────────

let relay = SatelliteRelay(nSatellites: 6)
relay.run(steps: 60)
let s = relay.summary()
print("Phase \(PHASE): Satellite Relay — 드론-위성 궤도 릴레이 통신")
print("Satellites: \(s["satellites"]!), Relayed: \(s["messages_relayed"]!)")
print("Orbital LEO altitude: \(s["orbital_altitude_km"]!) km — handover ready")
