// Phase 529: Satellite Relay — Swift
// SDACS satellite-based relay communication for beyond-LOS drone operations

import Foundation

// Phase 529 marker — orbital satellite relay with handover protocol

// MARK: - Orbital mechanics

struct SatelliteOrbit {
    let inclination:  Double  // degrees
    let altitude:     Double  // km above Earth surface
    let period:       Double  // orbital period in seconds
    let eccentricity: Double  // 0 = circular

    static let earthRadiusKm = 6371.0

    var semiMajorAxis: Double {
        return Self.earthRadiusKm + altitude
    }

    var orbitalSpeed: Double {
        let mu = 3.986e14  // Earth's gravitational parameter m^3/s^2
        let r  = semiMajorAxis * 1000  // convert to meters
        return sqrt(mu / r)
    }
}

// MARK: - Satellite node

class SatelliteNode {
    let nodeId:    String
    let name:      String
    let orbit:     SatelliteOrbit
    var isActive:  Bool
    var latency:   Double  // ms
    var bandwidth: Double  // Mbps

    private(set) var connectedDrones: Set<String> = []
    private(set) var relayCount:      Int = 0

    init(nodeId: String, name: String, orbit: SatelliteOrbit,
         latency: Double = 250, bandwidth: Double = 10.0) {
        self.nodeId    = nodeId
        self.name      = name
        self.orbit     = orbit
        self.isActive  = true
        self.latency   = latency
        self.bandwidth = bandwidth
    }

    func isVisibleFrom(droneAlt: Double, droneLat: Double, droneLon: Double) -> Bool {
        // Simplified visibility: satellite is above horizon if elevation > 5 degrees
        let minElevation = 5.0
        let earthR = SatelliteOrbit.earthRadiusKm
        let satR   = earthR + orbit.altitude
        let cosMin = earthR / satR * cos(minElevation * .pi / 180)
        return cosMin < 1.0  // simplified always-visible for LEO
    }

    func connect(droneId: String) -> Bool {
        guard isActive else { return false }
        connectedDrones.insert(droneId)
        return true
    }

    func disconnect(droneId: String) {
        connectedDrones.remove(droneId)
    }

    func relay(packet: DataPacket) -> DataPacket? {
        guard isActive, connectedDrones.contains(packet.sourceId) else { return nil }
        relayCount += 1
        return DataPacket(
            packetId:    packet.packetId,
            sourceId:    packet.sourceId,
            destId:      packet.destId,
            payload:     packet.payload,
            hopCount:    packet.hopCount + 1,
            relayedBy:   nodeId,
            timestamp:   Date()
        )
    }
}

// MARK: - Data packet

struct DataPacket {
    let packetId:  UUID
    let sourceId:  String
    let destId:    String
    let payload:   Data
    let hopCount:  Int
    let relayedBy: String?
    let timestamp: Date

    init(packetId: UUID = UUID(), sourceId: String, destId: String,
         payload: Data, hopCount: Int = 0, relayedBy: String? = nil,
         timestamp: Date = Date()) {
        self.packetId  = packetId
        self.sourceId  = sourceId
        self.destId    = destId
        self.payload   = payload
        self.hopCount  = hopCount
        self.relayedBy = relayedBy
        self.timestamp = timestamp
    }
}

// MARK: - Handover protocol

struct HandoverEvent {
    let droneId:   String
    let fromSat:   String
    let toSat:     String
    let timestamp: Date
    let reason:    HandoverReason
}

enum HandoverReason {
    case signalDegraded
    case betterCoverage
    case loadBalancing
    case satelliteUnavailable
}

class SatelliteRelayNetwork {
    private var satellites: [String: SatelliteNode] = [:]
    private var droneAssignments: [String: String]   = [:]  // droneId -> satId
    private var handoverLog: [HandoverEvent]          = []

    func addSatellite(_ sat: SatelliteNode) {
        satellites[sat.nodeId] = sat
    }

    func registerDrone(droneId: String) -> String? {
        guard let sat = satellites.values.first(where: { $0.isActive }) else {
            return nil
        }
        _ = sat.connect(droneId: droneId)
        droneAssignments[droneId] = sat.nodeId
        return sat.nodeId
    }

    func handover(droneId: String, targetSatId: String) -> Bool {
        guard let currentSatId = droneAssignments[droneId],
              let currentSat   = satellites[currentSatId],
              let targetSat    = satellites[targetSatId],
              targetSat.isActive else { return false }

        currentSat.disconnect(droneId: droneId)
        _ = targetSat.connect(droneId: droneId)
        droneAssignments[droneId] = targetSatId

        handoverLog.append(HandoverEvent(
            droneId:   droneId,
            fromSat:   currentSatId,
            toSat:     targetSatId,
            timestamp: Date(),
            reason:    .betterCoverage
        ))
        return true
    }

    func route(_ packet: DataPacket) -> DataPacket? {
        guard let satId = droneAssignments[packet.sourceId],
              let sat   = satellites[satId] else { return nil }
        return sat.relay(packet: packet)
    }

    func networkStats() -> [String: Any] {
        let totalRelays = satellites.values.reduce(0) { $0 + $1.relayCount }
        return [
            "satellites":   satellites.count,
            "active_sats":  satellites.values.filter { $0.isActive }.count,
            "connected":    droneAssignments.count,
            "total_relays": totalRelays,
            "handovers":    handoverLog.count,
        ]
    }
}

// MARK: - Entry point

let leo = SatelliteOrbit(inclination: 53.0, altitude: 550, period: 5640, eccentricity: 0.001)
let sat1 = SatelliteNode(nodeId: "SAT-001", name: "SDACS-LEO-1", orbit: leo)
let sat2 = SatelliteNode(nodeId: "SAT-002", name: "SDACS-LEO-2", orbit: leo, latency: 240)

let network = SatelliteRelayNetwork()
network.addSatellite(sat1)
network.addSatellite(sat2)

if let assignedSat = network.registerDrone(droneId: "D001") {
    print("Phase 529: Drone D001 connected to satellite \(assignedSat)")
}
let packet = DataPacket(sourceId: "D001", destId: "GCS",
                        payload: "telemetry".data(using: .utf8)!)
if let relayed = network.route(packet) {
    print("Packet relayed via \(relayed.relayedBy ?? "?"), hop=\(relayed.hopCount)")
}
print("Network stats: \(network.networkStats())")
