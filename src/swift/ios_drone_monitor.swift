// ios_drone_monitor.swift - iOS drone monitoring app for SDACS
import Foundation
import Combine

struct DroneState: Codable {
    let id: String
    let latitude: Double
    let longitude: Double
    let altitude: Double
    let battery: Int
    let status: String
}

class DroneMonitorViewModel: ObservableObject {
    @Published var drones: [DroneState] = []
    @Published var isConnected = false
    private var cancellables = Set<AnyCancellable>()
    private let apiBase: String

    init(apiBase: String) {
        self.apiBase = apiBase
    }

    func fetchSnapshot() {
        guard let url = URL(string: "\(apiBase)/api/v1/snapshot") else { return }
        URLSession.shared.dataTaskPublisher(for: url)
            .map(\.data)
            .decode(type: [DroneState].self, decoder: JSONDecoder())
            .receive(on: DispatchQueue.main)
            .sink(receiveCompletion: { _ in }, receiveValue: { [weak self] states in
                self?.drones = states
                self?.isConnected = true
            })
            .store(in: &cancellables)
    }
}
