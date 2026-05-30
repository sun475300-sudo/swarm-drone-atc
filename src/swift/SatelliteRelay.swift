// SDACS Satellite Relay — Swift (Phase 529)
// 드론 군집 위성 릴레이 통신 (orbital handover)

import Foundation

// 위성 궤도 정보
struct OrbitalParameters {
    let satelliteId: String
    let altitude: Double   // km
    let inclination: Double // degrees
    let period: Double     // minutes
    var elevation: Double  // degrees above horizon
}

// 핸드오버(handover) 이벤트
struct HandoverEvent {
    let fromSatellite: String
    let toSatellite: String
    let droneId: String
    let timestamp: Date
    let signalQuality: Double
}

// 위성 선택 알고리즘 (Phase 529)
class SatelliteSelector {
    private var satellites: [OrbitalParameters] = []
    private let minElevation: Double = 10.0  // degrees

    func addSatellite(_ sat: OrbitalParameters) {
        satellites.append(sat)
    }

    func bestSatellite(for droneId: String) -> OrbitalParameters? {
        satellites
            .filter { $0.elevation >= minElevation }
            .max(by: { $0.elevation < $1.elevation })
    }

    func handoverNeeded(current: OrbitalParameters) -> Bool {
        current.elevation < minElevation + 5.0
    }
}

// 위성 릴레이 채널
class SatelliteRelayChannel {
    private var selector = SatelliteSelector()
    private var currentSatellite: OrbitalParameters?
    private var handoverLog: [HandoverEvent] = []
    private let droneId: String

    init(droneId: String) {
        self.droneId = droneId
    }

    func registerSatellite(_ orbital: OrbitalParameters) {
        selector.addSatellite(orbital)
    }

    // 위성 연결 및 필요 시 handover 수행
    func connect() -> OrbitalParameters? {
        guard let best = selector.bestSatellite(for: droneId) else { return nil }

        if let cur = currentSatellite, cur.satelliteId != best.satelliteId {
            let event = HandoverEvent(
                fromSatellite: cur.satelliteId,
                toSatellite: best.satelliteId,
                droneId: droneId,
                timestamp: Date(),
                signalQuality: best.elevation / 90.0
            )
            handoverLog.append(event)
        }
        currentSatellite = best
        return best
    }

    func transmit(data: Data) -> Bool {
        guard let sat = currentSatellite, sat.elevation >= 10.0 else { return false }
        // 신호 품질 기반 전송 성공률
        let successProbability = (sat.elevation - 10.0) / 80.0
        return Double.random(in: 0...1) < successProbability
    }

    var handoverCount: Int { handoverLog.count }
    var isConnected: Bool { currentSatellite != nil }
    var currentLink: OrbitalParameters? { currentSatellite }
}

// Orbital 계산기
struct OrbitalMechanics {
    static func elevationAngle(satelliteAltitude: Double, groundRange: Double) -> Double {
        let earthRadius = 6371.0  // km
        let slantRange = sqrt(pow(groundRange, 2) + pow(satelliteAltitude + earthRadius, 2) - pow(earthRadius, 2))
        let sinEl = (satelliteAltitude + earthRadius - slantRange * cos(groundRange / earthRadius)) / slantRange
        return asin(max(-1.0, min(1.0, sinEl))) * 180.0 / .pi
    }

    static func orbitalPeriod(altitude: Double) -> Double {
        let earthRadius = 6371.0
        let mu = 398600.4418  // km^3/s^2
        let a = earthRadius + altitude
        return 2 * .pi * sqrt(pow(a, 3) / mu) / 60.0  // minutes
    }
}
