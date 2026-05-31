// ios_drone_monitor.swift
// Swift iOS stub for real-time drone monitoring.
// Connects to the swarm dashboard API and renders telemetry on-screen.

import UIKit
import Foundation
import Combine

// MARK: - Data Model

struct DroneTelemetry: Codable, Identifiable {
    let id: String
    let droneId: String
    let positionX: Double
    let positionY: Double
    let altitudeM: Double
    let velocityMs: Double
    let batteryPct: Int
    let state: String
}

// MARK: - Network Layer

final class DroneAPIClient {
    private let baseURL = URL(string: "http://localhost:3000/api")!
    private var cancellables = Set<AnyCancellable>()

    func fetchDrones(completion: @escaping ([DroneTelemetry]) -> Void) {
        let url = baseURL.appendingPathComponent("drones")
        URLSession.shared.dataTaskPublisher(for: url)
            .map(\.data)
            .decode(type: [DroneTelemetry].self, decoder: JSONDecoder())
            .replaceError(with: [])
            .receive(on: DispatchQueue.main)
            .sink(receiveValue: completion)
            .store(in: &cancellables)
    }
}

// MARK: - View Controller

class DroneMonitorViewController: UIViewController {
    private let apiClient = DroneAPIClient()
    private var drones: [DroneTelemetry] = []
    private var refreshTimer: Timer?

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Swarm Monitor"
        view.backgroundColor = .systemBackground
        startPolling()
    }

    private func startPolling() {
        refreshTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            self?.apiClient.fetchDrones { drones in
                self?.drones = drones
                // TODO: update table view / map overlay
            }
        }
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        refreshTimer?.invalidate()
    }
}
