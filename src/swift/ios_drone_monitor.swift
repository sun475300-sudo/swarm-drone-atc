// SDACS iOS Drone Monitor — Swift (Phase 612)
// iOS 드론 군집 모니터링 앱 (SwiftUI + Combine)

import Foundation
import Combine

// 드론 상태
public struct DroneInfo: Identifiable, Equatable {
    public let id: String
    public var x: Double
    public var y: Double
    public var altitude: Double
    public var battery: Double
    public var state: String
    public var lastUpdate: Date

    public var isLowBattery: Bool { battery < 20 }
    public var isActive: Bool { state == "FLYING" || state == "HOVERING" }
}

// 모니터링 뷰 모델
public class DroneMonitorViewModel: ObservableObject {
    @Published public var drones: [DroneInfo] = []
    @Published public var conflicts: [(String, String, Double)] = []
    @Published public var isConnected = false

    private var cancellables = Set<AnyCancellable>()
    private let separationThreshold = 50.0

    public init() {}

    public func updateDrone(_ info: DroneInfo) {
        if let idx = drones.firstIndex(where: { $0.id == info.id }) {
            drones[idx] = info
        } else {
            drones.append(info)
        }
        detectConflicts()
    }

    private func detectConflicts() {
        var found: [(String, String, Double)] = []
        for i in drones.indices {
            for j in (i+1)..<drones.count {
                let a = drones[i], b = drones[j]
                let dist = sqrt(pow(a.x - b.x, 2) + pow(a.y - b.y, 2))
                if dist < separationThreshold {
                    found.append((a.id, b.id, dist))
                }
            }
        }
        conflicts = found
    }

    public var activeDroneCount: Int { drones.filter(\.isActive).count }
    public var lowBatteryCount: Int { drones.filter(\.isLowBattery).count }
    public var averageAltitude: Double {
        drones.isEmpty ? 0 : drones.map(\.altitude).reduce(0, +) / Double(drones.count)
    }
    public var averageBattery: Double {
        drones.isEmpty ? 0 : drones.map(\.battery).reduce(0, +) / Double(drones.count)
    }

    // 텔레메트리 시뮬레이션
    public func startSimulation(n: Int = 10) {
        isConnected = true
        for i in 0..<n {
            let info = DroneInfo(
                id: "D-\(String(format: "%03d", i))",
                x: Double.random(in: -500...500),
                y: Double.random(in: -500...500),
                altitude: Double.random(in: 50...200),
                battery: Double.random(in: 20...100),
                state: "FLYING",
                lastUpdate: Date()
            )
            updateDrone(info)
        }
    }
}

// WebSocket 클라이언트 (URLSession 기반)
public class TelemetryWebSocketClient {
    private var webSocketTask: URLSessionWebSocketTask?
    private let session = URLSession.shared
    public var onMessage: ((Data) -> Void)?

    public func connect(to url: URL) {
        webSocketTask = session.webSocketTask(with: url)
        webSocketTask?.resume()
        receiveLoop()
    }

    private func receiveLoop() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let msg):
                if case .data(let data) = msg { self?.onMessage?(data) }
                self?.receiveLoop()
            case .failure: break
            }
        }
    }

    public func disconnect() { webSocketTask?.cancel() }
}
