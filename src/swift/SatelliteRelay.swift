// Phase 529: SatelliteRelay — Swift 기반 위성 릴레이 통신
// SDACS Satellite Relay for Beyond-Line-of-Sight Drone Communication

import Foundation

// 위성 궤도 정보 (orbital parameters)
struct OrbitalParameters {
    let satelliteId: String
    let altitude: Double      // km
    let inclination: Double   // degrees
    let period: Double        // minutes
    let coverage: Double      // degrees (half-angle)

    var orbitalRadius: Double { 6371.0 + altitude }
}

// 위성 링크 상태
enum SatelliteLinkStatus {
    case connected
    case handover    // 위성 핸드오버 중
    case searching
    case lost
}

// 위성 릴레이 채널
class SatelliteRelayChannel {
    let satellite: OrbitalParameters
    var status: SatelliteLinkStatus = .searching
    var signalStrength: Double = 0.0
    var dataRate: Double = 0.0  // Mbps
    var latency: Double = 0.0   // ms

    init(satellite: OrbitalParameters) {
        self.satellite = satellite
    }

    func computeLatency() -> Double {
        // 왕복 지연 = 2 * 거리 / 광속
        return 2.0 * satellite.altitude * 1000.0 / 299_792_458.0 * 1000.0
    }

    func connect(droneAlt: Double) {
        let slantRange = sqrt(satellite.altitude * satellite.altitude + droneAlt * droneAlt / 1_000_000.0)
        signalStrength = max(0, 1.0 - slantRange / 1000.0)
        dataRate = signalStrength * 50.0
        latency = computeLatency()
        status = signalStrength > 0.1 ? .connected : .lost
    }
}

// 위성 핸드오버 관리자
class SatelliteHandoverManager {
    var channels: [SatelliteRelayChannel]
    var activeChannelIndex: Int = 0
    var handoverCount: Int = 0
    var handoverThreshold: Double = 0.3

    init(satellites: [OrbitalParameters]) {
        channels = satellites.map { SatelliteRelayChannel(satellite: $0) }
    }

    var activeChannel: SatelliteRelayChannel? {
        guard !channels.isEmpty else { return nil }
        return channels[activeChannelIndex]
    }

    // 최적 위성으로 핸드오버 수행
    func performHandover(droneAlt: Double) -> Bool {
        channels.forEach { $0.connect(droneAlt: droneAlt) }

        guard let best = channels.enumerated().max(by: { $0.element.signalStrength < $1.element.signalStrength }),
              best.element.signalStrength > handoverThreshold else {
            activeChannel?.status = .lost
            return false
        }

        if best.offset != activeChannelIndex {
            activeChannel?.status = .handover
            activeChannelIndex = best.offset
            handoverCount += 1
            channels[activeChannelIndex].status = .connected
            return true
        }
        return false
    }

    func summary() -> String {
        let active = activeChannel
        return "위성릴레이: 활성위성=\(active?.satellite.satelliteId ?? "N/A") " +
               "신호=\(String(format: "%.1f", (active?.signalStrength ?? 0) * 100))% " +
               "핸드오버=\(handoverCount)회"
    }
}

// BLOS (Beyond-Line-of-Sight) 드론 링크
class BLOSLink {
    let droneId: Int
    let handoverManager: SatelliteHandoverManager
    var messageQueue: [(String, Double)] = []

    init(droneId: Int, satellites: [OrbitalParameters]) {
        self.droneId = droneId
        handoverManager = SatelliteHandoverManager(satellites: satellites)
    }

    func connect(droneAlt: Double) {
        _ = handoverManager.performHandover(droneAlt: droneAlt)
    }

    func sendTelemetry(lat: Double, lon: Double, alt: Double, timestamp: Double) {
        let msg = "D\(droneId)|lat=\(lat)|lon=\(lon)|alt=\(alt)|t=\(timestamp)"
        messageQueue.append((msg, timestamp))
        if let ch = handoverManager.activeChannel, ch.status == .connected {
            // 전송 성공
        }
    }

    var isConnected: Bool {
        handoverManager.activeChannel?.status == .connected
    }
}

// 메인 실행
let satellites = [
    OrbitalParameters(satelliteId: "SAT-LEO-1", altitude: 550, inclination: 53.0, period: 95.5, coverage: 60.0),
    OrbitalParameters(satelliteId: "SAT-LEO-2", altitude: 600, inclination: 45.0, period: 97.0, coverage: 55.0),
    OrbitalParameters(satelliteId: "SAT-MEO-1", altitude: 8000, inclination: 55.0, period: 290.0, coverage: 70.0),
]

print("SDACS Satellite Relay — Phase 529\n")
print("위성 수: \(satellites.count)")
satellites.forEach { sat in
    print("  \(sat.satelliteId): 고도=\(sat.altitude)km 커버리지=\(sat.coverage)°")
}

let link = BLOSLink(droneId: 1, satellites: satellites)
link.connect(droneAlt: 50.0)

// 텔레메트리 전송 시뮬레이션
for i in 0..<5 {
    link.sendTelemetry(lat: 37.5 + Double(i) * 0.001, lon: 127.0, alt: 50.0 + Double(i), timestamp: Double(i))
    _ = link.handoverManager.performHandover(droneAlt: 50.0 + Double(i))
}

print("\n\(link.handoverManager.summary())")
print("메시지 큐: \(link.messageQueue.count)건")
print("위성 릴레이 통신 완료.")
