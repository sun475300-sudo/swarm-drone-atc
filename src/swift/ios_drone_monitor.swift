// iOS Drone Monitor — SDACS Phase 612
import Foundation

struct DroneStatus: Codable {
    let id: String
    let lat: Double
    let lon: Double
    let alt: Double
    let battery: Int
}

class DroneMonitor: ObservableObject {
    @Published var drones: [DroneStatus] = []
    
    func fetchDrones() async {
        // Fetch from SDACS API
    }
}
