/**
 * Phase 284: Swift Emergency Recovery — 비상 복구 시스템
 * 프로토콜 지향 프로그래밍, 열거형 기반 상태 머신.
 */

import Foundation

enum EmergencyType: String, CaseIterable {
    case motorFailure = "motor_failure"
    case batteryCritical = "battery_critical"
    case gpsLoss = "gps_loss"
    case commLoss = "comm_loss"
    case collisionImminent = "collision_imminent"
    case geofenceBreach = "geofence_breach"
    case sensorMalfunction = "sensor_malfunction"
    case weatherExtreme = "weather_extreme"
}

enum RecoveryAction: String {
    case emergencyLand = "emergency_land"
    case returnToBase = "return_to_base"
    case hoverInPlace = "hover_in_place"
    case altitudeChange = "altitude_change"
    case speedReduction = "speed_reduction"
    case missionAbort = "mission_abort"
    case parachuteDeploy = "parachute_deploy"
}

enum RecoveryStatus: String {
    case detected, responding, executing, resolved, escalated
}

struct EmergencyEvent {
    let eventId: String
    let droneId: String
    let type: EmergencyType
    let severity: Double
    let position: (x: Double, y: Double, z: Double)
    var status: RecoveryStatus = .detected
    var actionsTaken: [RecoveryAction] = []
    var resolved: Bool = false
}

struct RecoveryPlan {
    let eventId: String
    let actions: [RecoveryAction]
    let priority: Int
    let successProbability: Double
}

protocol EmergencyRecoverable {
    func detectEmergency(droneId: String, type: EmergencyType, severity: Double,
                        position: (Double, Double, Double)) -> EmergencyEvent
    func executeRecovery(eventId: String) -> Bool
    func getActiveEmergencies() -> [EmergencyEvent]
}

class EmergencyRecoverySystem: EmergencyRecoverable {
    private static let recoveryMatrix: [EmergencyType: [RecoveryAction]] = [
        .motorFailure: [.emergencyLand, .parachuteDeploy],
        .batteryCritical: [.returnToBase, .emergencyLand],
        .gpsLoss: [.hoverInPlace, .emergencyLand],
        .commLoss: [.returnToBase, .hoverInPlace],
        .collisionImminent: [.altitudeChange, .speedReduction],
        .geofenceBreach: [.returnToBase, .missionAbort],
        .sensorMalfunction: [.hoverInPlace, .returnToBase],
        .weatherExtreme: [.emergencyLand, .altitudeChange],
    ]

    private var events: [String: EmergencyEvent] = [:]
    private var plans: [String: RecoveryPlan] = [:]
    private var eventCounter = 0
    private var resolvedCount = 0
    private var escalatedCount = 0

    func detectEmergency(droneId: String, type: EmergencyType, severity: Double,
                        position: (Double, Double, Double)) -> EmergencyEvent {
        eventCounter += 1
        let eid = String(format: "EMG-%04d", eventCounter)
        let event = EmergencyEvent(
            eventId: eid, droneId: droneId, type: type,
            severity: min(1.0, max(0.0, severity)),
            position: position
        )
        events[eid] = event

        let actions = Self.recoveryMatrix[type] ?? [.hoverInPlace]
        let plan = RecoveryPlan(
            eventId: eid, actions: actions,
            priority: Int(severity * 10),
            successProbability: max(0.3, 1.0 - severity * 0.5)
        )
        plans[eid] = plan
        return event
    }

    func executeRecovery(eventId: String) -> Bool {
        guard var event = events[eventId], let plan = plans[eventId] else { return false }
        event.status = .executing
        event.actionsTaken = plan.actions

        let success = Double.random(in: 0...1) < plan.successProbability
        if success {
            event.status = .resolved
            event.resolved = true
            resolvedCount += 1
        } else {
            event.status = .escalated
            escalatedCount += 1
        }
        events[eventId] = event
        return success
    }

    func resolveEvent(eventId: String) -> Bool {
        guard var event = events[eventId] else { return false }
        event.status = .resolved
        event.resolved = true
        events[eventId] = event
        resolvedCount += 1
        return true
    }

    func getActiveEmergencies() -> [EmergencyEvent] {
        events.values.filter { !$0.resolved }
    }

    func summary() -> [String: Any] {
        let active = events.values.filter { !$0.resolved }.count
        var byType: [String: Int] = [:]
        for event in events.values {
            byType[event.type.rawValue, default: 0] += 1
        }
        return [
            "totalEvents": events.count,
            "activeEmergencies": active,
            "resolved": resolvedCount,
            "escalated": escalatedCount,
            "byType": byType,
        ]
    }
}
