// Phase 612: iOS Drone Monitor — Swift
// SDACS iOS application for real-time drone fleet monitoring

import Foundation

struct DroneMonitorState {
    var droneId:   String
    var latitude:  Double
    var longitude: Double
    var altitude:  Double
    var battery:   Double
    var isActive:  Bool
}

class DroneMonitorViewModel {
    private(set) var drones: [DroneMonitorState] = []
    var onUpdate: (() -> Void)?

    func refresh() {
        onUpdate?()
    }

    func addDrone(_ state: DroneMonitorState) {
        drones.append(state)
        onUpdate?()
    }
}
