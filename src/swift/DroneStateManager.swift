///
/// SDACS 드론 상태 관리자 — Swift
/// ================================
/// 드론 FSM (유한 상태 머신) + 이벤트 기반 전이
///
/// 기능:
///   - 드론 상태 머신 (12 상태, 20+ 전이)
///   - 이벤트 기반 자동 전이
///   - 상태 이력 추적
///   - 배터리/위치 기반 조건부 전이
///

import Foundation

// MARK: - 상태 정의

enum DroneState: String, CaseIterable {
    case idle = "IDLE"
    case preflight = "PREFLIGHT"
    case armed = "ARMED"
    case takeoff = "TAKEOFF"
    case climbing = "CLIMBING"
    case cruise = "CRUISE"
    case descending = "DESCENDING"
    case approach = "APPROACH"
    case landing = "LANDING"
    case emergency = "EMERGENCY"
    case returnToBase = "RTL"
    case grounded = "GROUNDED"
}

enum DroneEvent: String {
    case startPreflight
    case preflightComplete
    case armMotors
    case inititateTakeoff
    case reachCruiseAlt
    case startDescent
    case approachWaypoint
    case initiateLanding
    case touchDown
    case emergencyDeclare
    case emergencyResolve
    case batteryLow
    case returnToBase
    case missionComplete
    case resetSystem
}

// MARK: - 전이 규칙

struct Transition {
    let from: DroneState
    let event: DroneEvent
    let to: DroneState
    let guard: ((DroneContext) -> Bool)?
    let action: ((inout DroneContext) -> Void)?
}

struct DroneContext {
    var droneId: String
    var battery: Double = 100.0
    var altitude: Double = 0.0
    var speed: Double = 0.0
    var position: (x: Double, y: Double, z: Double) = (0, 0, 0)
    var missionId: String? = nil
    var errorCode: Int = 0
    var stateHistory: [(state: DroneState, timestamp: Date)] = []
    var eventLog: [(event: DroneEvent, timestamp: Date)] = []
}

// MARK: - 상태 머신

class DroneStateMachine {
    private(set) var currentState: DroneState
    private(set) var context: DroneContext
    private var transitions: [Transition] = []

    init(droneId: String) {
        self.currentState = .idle
        self.context = DroneContext(droneId: droneId)
        self.context.stateHistory.append((state: .idle, timestamp: Date()))
        setupTransitions()
    }

    private func setupTransitions() {
        let t = { (from: DroneState, event: DroneEvent, to: DroneState,
                   guard g: ((DroneContext) -> Bool)? = nil,
                   action a: ((inout DroneContext) -> Void)? = nil) in
            Transition(from: from, event: event, to: to, guard: g, action: a)
        }

        transitions = [
            // 정상 비행 사이클
            t(.idle, .startPreflight, .preflight),
            t(.preflight, .preflightComplete, .armed,
              guard: { $0.battery > 20 }),
            t(.armed, .inititateTakeoff, .takeoff,
              guard: { $0.battery > 15 }),
            t(.takeoff, .reachCruiseAlt, .climbing),
            t(.climbing, .reachCruiseAlt, .cruise),
            t(.cruise, .startDescent, .descending),
            t(.cruise, .approachWaypoint, .approach),
            t(.descending, .approachWaypoint, .approach),
            t(.approach, .initiateLanding, .landing),
            t(.landing, .touchDown, .grounded,
              action: { ctx in ctx.altitude = 0; ctx.speed = 0 }),
            t(.grounded, .resetSystem, .idle),

            // RTL (Return to Launch)
            t(.cruise, .batteryLow, .returnToBase,
              guard: { $0.battery < 20 }),
            t(.cruise, .returnToBase, .returnToBase),
            t(.descending, .batteryLow, .returnToBase,
              guard: { $0.battery < 15 }),
            t(.returnToBase, .approachWaypoint, .approach),

            // 비상
            t(.cruise, .emergencyDeclare, .emergency),
            t(.climbing, .emergencyDeclare, .emergency),
            t(.descending, .emergencyDeclare, .emergency),
            t(.takeoff, .emergencyDeclare, .emergency),
            t(.approach, .emergencyDeclare, .emergency),
            t(.emergency, .emergencyResolve, .returnToBase),
            t(.emergency, .touchDown, .grounded),

            // 미션 완료
            t(.cruise, .missionComplete, .descending),
        ]
    }

    /// 이벤트 처리 → 상태 전이
    @discardableResult
    func handleEvent(_ event: DroneEvent) -> Bool {
        let matching = transitions.filter { t in
            t.from == currentState && t.event == event
        }

        for transition in matching {
            // Guard 조건 체크
            if let guard_ = transition.guard {
                if !guard_(context) { continue }
            }

            // 전이 실행
            let oldState = currentState
            currentState = transition.to

            // Action 실행
            transition.action?(&context)

            // 이력 기록
            context.stateHistory.append((state: currentState, timestamp: Date()))
            context.eventLog.append((event: event, timestamp: Date()))

            return true
        }

        return false // 전이 불가
    }

    /// 배터리 업데이트 → 자동 RTL 트리거
    func updateBattery(_ pct: Double) {
        context.battery = pct
        if pct < 20 && currentState == .cruise {
            handleEvent(.batteryLow)
        }
    }

    /// 위치 업데이트
    func updatePosition(x: Double, y: Double, z: Double) {
        context.position = (x, y, z)
        context.altitude = z
    }

    /// 상태 이력
    var stateHistory: [(state: DroneState, timestamp: Date)] {
        context.stateHistory
    }

    /// 통계 요약
    func summary() -> [String: Any] {
        return [
            "droneId": context.droneId,
            "currentState": currentState.rawValue,
            "battery": context.battery,
            "altitude": context.altitude,
            "totalTransitions": context.stateHistory.count - 1,
            "totalEvents": context.eventLog.count,
            "errorCode": context.errorCode
        ]
    }
}
