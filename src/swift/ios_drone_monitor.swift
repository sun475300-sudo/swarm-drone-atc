// Phase 612 — Swift iOS Drone Monitor
// Real-time swarm monitoring app for iOS using Combine + SwiftUI

import Foundation
import Combine

struct DroneState: Codable, Identifiable {
    let id: String
    let x: Double
    let y: Double
    let z: Double
    let batteryPct: Double
    let flightPhase: String
}

struct SwarmMetrics: Codable {
    let totalDrones: Int
    let activeDrones: Int
    let collisionCount: Int
    let conflictResolutionRate: Double
}

@MainActor
final class DroneMonitorViewModel: ObservableObject {
    @Published var drones: [DroneState] = []
    @Published var metrics: SwarmMetrics?
    @Published var isConnected = false

    private var cancellables = Set<AnyCancellable>()
    private let baseURL: URL

    init(baseURL: URL = URL(string: "http://localhost:8000")!) {
        self.baseURL = baseURL
    }

    func connect() {
        isConnected = true
        fetchDrones()
        fetchMetrics()
    }

    func fetchDrones() {
        URLSession.shared.dataTaskPublisher(for: baseURL.appendingPathComponent("api/drones"))
            .map(\.data)
            .decode(type: [DroneState].self, decoder: JSONDecoder())
            .replaceError(with: [])
            .receive(on: DispatchQueue.main)
            .sink { [weak self] in self?.drones = $0 }
            .store(in: &cancellables)
    }

    func fetchMetrics() {
        URLSession.shared.dataTaskPublisher(for: baseURL.appendingPathComponent("api/metrics"))
            .map(\.data)
            .decode(type: SwarmMetrics.self, decoder: JSONDecoder())
            .replaceError(with: nil)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] in self?.metrics = $0 }
            .store(in: &cancellables)
    }
}
