/// Phase 349: Swift Predictive Maintenance
/// Weibull analysis + anomaly detection for drone components.
/// Value types for thread-safe health monitoring.

import Foundation

// MARK: - Types

enum ComponentType: String, CaseIterable {
    case motor, esc, battery, propeller, frame, sensorImu, sensorGps, flightController
}

enum HealthStatus: String {
    case healthy, degraded, warning, critical, failed
}

enum AlertSeverity: String {
    case info, low, medium, high, critical
}

struct SensorReading {
    let timestamp: Double
    let componentId: String
    let vibration: Double
    let temperature: Double
    let currentDraw: Double
    let voltage: Double
    let rpm: Double
}

struct ComponentHealth {
    let componentId: String
    let componentType: ComponentType
    let healthScore: Double
    let status: HealthStatus
    let rulHours: Double
    let failureProbability: Double
    let trend: String
}

struct MaintenanceAlert {
    let alertId: String
    let componentId: String
    let severity: AlertSeverity
    let description: String
    let estimatedRul: Double
    let timestamp: Double
}

// MARK: - Weibull Distribution

struct WeibullParams {
    let shape: Double   // beta
    let scale: Double   // eta
    let location: Double

    init(shape: Double, scale: Double, location: Double = 0) {
        self.shape = shape
        self.scale = scale
        self.location = location
    }
}

class WeibullAnalyzer {
    private let params: [ComponentType: WeibullParams] = [
        .motor: WeibullParams(shape: 2.5, scale: 800),
        .esc: WeibullParams(shape: 2.0, scale: 1200),
        .battery: WeibullParams(shape: 3.0, scale: 500),
        .propeller: WeibullParams(shape: 1.8, scale: 300),
        .frame: WeibullParams(shape: 4.0, scale: 5000),
        .sensorImu: WeibullParams(shape: 2.2, scale: 2000),
        .sensorGps: WeibullParams(shape: 2.0, scale: 3000),
        .flightController: WeibullParams(shape: 3.5, scale: 4000),
    ]

    func reliability(_ type: ComponentType, hours: Double) -> Double {
        let p = params[type] ?? WeibullParams(shape: 2.0, scale: 1000)
        let t = max(hours - p.location, 0)
        return exp(-pow(t / p.scale, p.shape))
    }

    func failureRate(_ type: ComponentType, hours: Double) -> Double {
        let p = params[type] ?? WeibullParams(shape: 2.0, scale: 1000)
        let t = max(hours - p.location, 1e-10)
        return (p.shape / p.scale) * pow(t / p.scale, p.shape - 1)
    }

    func rulEstimate(_ type: ComponentType, currentHours: Double,
                     targetReliability: Double = 0.5) -> Double {
        let p = params[type] ?? WeibullParams(shape: 2.0, scale: 1000)
        let targetTime = p.scale * pow(-log(targetReliability), 1.0 / p.shape) + p.location
        return max(0, targetTime - currentHours)
    }
}

// MARK: - Anomaly Detector

class AnomalyDetector {
    private let windowSize: Int
    private let thresholdSigma: Double
    private var history: [String: [Double]] = [:]

    init(windowSize: Int = 50, thresholdSigma: Double = 3.0) {
        self.windowSize = windowSize
        self.thresholdSigma = thresholdSigma
    }

    func isAnomalous(componentId: String, value: Double) -> Bool {
        var hist = history[componentId] ?? []
        hist.append(value)
        if hist.count > windowSize * 2 {
            hist = Array(hist.suffix(windowSize * 2))
        }
        history[componentId] = hist

        guard hist.count >= windowSize else { return false }
        let window = Array(hist.suffix(windowSize))
        let mean = window.reduce(0, +) / Double(window.count)
        let variance = window.map { ($0 - mean) * ($0 - mean) }.reduce(0, +) / Double(window.count)
        let std = sqrt(variance)
        guard std > 1e-10 else { return false }
        return abs(value - mean) / std > thresholdSigma
    }
}

// MARK: - Predictive Maintenance Engine

class PredictiveMaintenanceEngine {
    private let weibull = WeibullAnalyzer()
    private let anomalyDetector = AnomalyDetector()
    private var components: [String: (ComponentType, Double)] = [:]
    private var healthRecords: [String: ComponentHealth] = [:]
    private var alerts: [MaintenanceAlert] = []
    private var readingCount = 0
    private var alertCounter = 0

    func registerComponent(_ id: String, type: ComponentType, initialHours: Double = 0) {
        components[id] = (type, initialHours)
    }

    func processReading(_ reading: SensorReading) -> ComponentHealth {
        readingCount += 1
        guard var (compType, hours) = components[reading.componentId] else {
            return ComponentHealth(componentId: reading.componentId,
                componentType: .motor, healthScore: 0, status: .failed,
                rulHours: 0, failureProbability: 1, trend: "unknown")
        }

        hours += 0.01
        components[reading.componentId] = (compType, hours)

        let reliability = weibull.reliability(compType, hours: hours)
        let rul = weibull.rulEstimate(compType, currentHours: hours)
        let failProb = 1.0 - reliability

        let vibAnomaly = anomalyDetector.isAnomalous("\(reading.componentId)_vib", value: reading.vibration)
        let tempAnomaly = anomalyDetector.isAnomalous("\(reading.componentId)_temp", value: reading.temperature)

        var healthScore = reliability * 100
        if vibAnomaly { healthScore *= 0.7 }
        if tempAnomaly { healthScore *= 0.8 }
        if reading.temperature > 80 { healthScore *= 0.6 }
        healthScore = max(0, min(100, healthScore))

        let status: HealthStatus
        switch healthScore {
        case 80...: status = .healthy
        case 60..<80: status = .degraded
        case 40..<60: status = .warning
        case 20..<40: status = .critical
        default: status = .failed
        }

        let prev = healthRecords[reading.componentId]
        let trend: String
        if let p = prev {
            if healthScore > p.healthScore + 2 { trend = "improving" }
            else if healthScore < p.healthScore - 2 { trend = "degrading" }
            else { trend = "stable" }
        } else { trend = "stable" }

        let health = ComponentHealth(
            componentId: reading.componentId,
            componentType: compType,
            healthScore: (healthScore * 10).rounded() / 10,
            status: status, rulHours: (rul * 10).rounded() / 10,
            failureProbability: (failProb * 10000).rounded() / 10000,
            trend: trend
        )
        healthRecords[reading.componentId] = health

        if [HealthStatus.warning, .critical, .failed].contains(status) {
            generateAlert(health, timestamp: reading.timestamp)
        }
        return health
    }

    private func generateAlert(_ health: ComponentHealth, timestamp: Double) {
        alertCounter += 1
        let severity: AlertSeverity
        let action: String
        switch health.status {
        case .warning: severity = .medium; action = "Schedule inspection"
        case .critical: severity = .high; action = "Immediate maintenance"
        case .failed: severity = .critical; action = "Ground and replace"
        default: severity = .info; action = "Monitor"
        }
        alerts.append(MaintenanceAlert(
            alertId: String(format: "MA-%06d", alertCounter),
            componentId: health.componentId,
            severity: severity,
            description: "\(health.componentType.rawValue) health=\(health.healthScore)% RUL=\(health.rulHours)h",
            estimatedRul: health.rulHours,
            timestamp: timestamp
        ))
    }

    func summary() -> [String: Any] {
        let scores = healthRecords.values.map { $0.healthScore }
        let avgHealth = scores.isEmpty ? 0 : scores.reduce(0, +) / Double(scores.count)
        return [
            "components": components.count,
            "readings": readingCount,
            "avgHealth": (avgHealth * 10).rounded() / 10,
            "alerts": alerts.count,
            "criticalAlerts": alerts.filter { $0.severity == .critical }.count,
        ]
    }
}
