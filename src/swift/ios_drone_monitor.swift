// Phase 612: iOS Drone Monitor — Swift Protocol
// iOS 드론 모니터링 클라이언트 프로토콜

import Foundation

struct DronePosition {
    let x: Double
    let y: Double
    let z: Double

    func distanceTo(_ other: DronePosition) -> Double {
        let dx = x - other.x
        let dy = y - other.y
        let dz = z - other.z
        return (dx*dx + dy*dy + dz*dz).squareRoot()
    }
}

struct DroneState {
    let droneId: String
    let position: DronePosition
    let battery: Double
    let status: String
    let timestamp: TimeInterval
}

enum AlertLevel: Int, Comparable {
    case info = 0
    case warning = 1
    case critical = 2
    case emergency = 3

    static func < (lhs: AlertLevel, rhs: AlertLevel) -> Bool {
        return lhs.rawValue < rhs.rawValue
    }
}

struct MonitorAlert {
    let droneId: String
    let level: AlertLevel
    let message: String
    let timestamp: TimeInterval
}

protocol DroneMonitorDelegate {
    func didReceiveUpdate(_ state: DroneState)
    func didReceiveAlert(_ alert: MonitorAlert)
    func didLoseConnection(droneId: String)
}

class DroneMonitorClient {
    var drones: [String: DroneState] = [:]
    var alerts: [MonitorAlert] = []
    var delegate: DroneMonitorDelegate?
    var isConnected: Bool = false

    func connect(serverURL: String) {
        isConnected = true
    }

    func disconnect() {
        isConnected = false
    }

    func processUpdate(_ state: DroneState) {
        drones[state.droneId] = state
        delegate?.didReceiveUpdate(state)

        if state.battery < 0.15 {
            let alert = MonitorAlert(
                droneId: state.droneId,
                level: .warning,
                message: "Low battery: \(Int(state.battery * 100))%",
                timestamp: state.timestamp
            )
            alerts.append(alert)
            delegate?.didReceiveAlert(alert)
        }
    }

    func getActiveDrones() -> [DroneState] {
        return drones.values.filter { $0.status != "idle" }
    }

    func getNearbyDrones(to position: DronePosition, radius: Double) -> [DroneState] {
        return drones.values.filter { state in
            state.position.distanceTo(position) <= radius
        }
    }

    func getSummary() -> (total: Int, active: Int, alerts: Int) {
        let active = getActiveDrones().count
        return (total: drones.count, active: active, alerts: alerts.count)
    }
}
