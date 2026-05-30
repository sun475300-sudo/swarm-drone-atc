// Phase 612: ios_drone_monitor — Swift/iOS 기반 드론 모니터링 앱
// SDACS iOS Drone Monitoring Application

import Foundation
import Combine

// 드론 상태 모델
struct DroneStatus: Codable, Identifiable {
    let id: Int
    let lat: Double
    let lon: Double
    let alt: Double
    let battery: Double
    let speed: Double
    let flightMode: String
    let isArmed: Bool
    let timestamp: TimeInterval

    enum CodingKeys: String, CodingKey {
        case id = "drone_id"
        case lat, lon, alt, battery, speed
        case flightMode = "flight_mode"
        case isArmed = "is_armed"
        case timestamp
    }

    var batteryColor: String {
        switch battery {
        case 50...: return "green"
        case 20..<50: return "yellow"
        default: return "red"
        }
    }
}

// 공역 스냅샷 모델
struct AirspaceSnapshot: Codable {
    let drones: [DroneStatus]
    let conflictCount: Int
    let resolutionRate: Double
    let timestamp: TimeInterval

    enum CodingKeys: String, CodingKey {
        case drones
        case conflictCount = "conflict_count"
        case resolutionRate = "resolution_rate"
        case timestamp
    }
}

// API 응답 래퍼
struct ApiResponse<T: Codable>: Codable {
    let success: Bool
    let data: T?
    let error: String?
}

// 드론 모니터링 서비스
class DroneMonitorService: ObservableObject {
    @Published var drones: [DroneStatus] = []
    @Published var conflictCount: Int = 0
    @Published var connectionStatus: ConnectionStatus = .disconnected
    @Published var lastError: String?

    private var webSocketTask: URLSessionWebSocketTask?
    private var refreshTimer: Timer?
    private let session: URLSession
    private let baseURL: URL
    private let wsURL: URL

    enum ConnectionStatus {
        case connected, disconnected, connecting, error
    }

    init(baseURL: String, wsURL: String) {
        self.baseURL = URL(string: baseURL)!
        self.wsURL = URL(string: wsURL)!
        self.session = URLSession(configuration: .default)
    }

    // 스냅샷 폴링 시작 (REST API)
    func startPolling(interval: TimeInterval = 1.0) {
        refreshTimer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            self?.fetchSnapshot()
        }
    }

    // WebSocket 연결
    func connectWebSocket() {
        connectionStatus = .connecting
        webSocketTask = session.webSocketTask(with: wsURL)
        webSocketTask?.resume()
        connectionStatus = .connected
        receiveMessage()
    }

    // 메시지 수신 루프
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self?.handleSnapshot(text)
                case .data(let data):
                    self?.handleSnapshot(String(data: data, encoding: .utf8) ?? "")
                @unknown default:
                    break
                }
                self?.receiveMessage()
            case .failure(let error):
                self?.connectionStatus = .error
                self?.lastError = error.localizedDescription
                DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                    self?.connectWebSocket()
                }
            }
        }
    }

    // 스냅샷 파싱
    private func handleSnapshot(_ json: String) {
        guard let data = json.data(using: .utf8) else { return }
        do {
            let snapshot = try JSONDecoder().decode(AirspaceSnapshot.self, from: data)
            DispatchQueue.main.async {
                self.drones = snapshot.drones
                self.conflictCount = snapshot.conflictCount
            }
        } catch {
            lastError = "Parse error: \(error)"
        }
    }

    // REST API 스냅샷 조회
    private func fetchSnapshot() {
        let url = baseURL.appendingPathComponent("api/airspace/snapshot")
        session.dataTask(with: url) { [weak self] data, _, error in
            if let error = error {
                DispatchQueue.main.async { self?.lastError = error.localizedDescription }
                return
            }
            guard let data = data else { return }
            do {
                let response = try JSONDecoder().decode(ApiResponse<AirspaceSnapshot>.self, from: data)
                if let snapshot = response.data {
                    DispatchQueue.main.async {
                        self?.drones = snapshot.drones
                        self?.conflictCount = snapshot.conflictCount
                    }
                }
            } catch {
                DispatchQueue.main.async { self?.lastError = "Decode error: \(error)" }
            }
        }.resume()
    }

    // 정리
    deinit {
        refreshTimer?.invalidate()
        webSocketTask?.cancel(with: .goingAway, reason: nil)
    }
}

// Phase 612 진입점
print("SDACS iOS Drone Monitor — Phase 612")
let service = DroneMonitorService(
    baseURL: "http://localhost:8080",
    wsURL: "ws://localhost:8765"
)
print("Monitor service initialized: \(service.connectionStatus)")
