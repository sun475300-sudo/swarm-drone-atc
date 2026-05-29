/// Phase 329: Swift Intrusion Detection System
/// Protocol-oriented network anomaly detection.
/// Value types for safe concurrent analysis.

import Foundation

// MARK: - Types

enum ThreatLevel: String, CaseIterable {
    case none, low, medium, high, critical
}

enum AttackType: String {
    case none, dos, spoofing, jamming, injection, replay, mitm, unknown
}

struct NetworkPacket {
    let sourceId: String
    let destId: String
    let packetType: String  // telemetry, command, ack, heartbeat
    let sizeBytes: Int
    let timestamp: Double
    let isEncrypted: Bool

    init(sourceId: String, destId: String, packetType: String,
         sizeBytes: Int, timestamp: Double, isEncrypted: Bool = true) {
        self.sourceId = sourceId
        self.destId = destId
        self.packetType = packetType
        self.sizeBytes = sizeBytes
        self.timestamp = timestamp
        self.isEncrypted = isEncrypted
    }
}

struct ThreatAlert {
    let alertId: String
    let threatLevel: ThreatLevel
    let attackType: AttackType
    let sourceId: String
    let description: String
    let confidence: Double
    let timestamp: Double
}

// MARK: - Isolation Tree

class IsolationNode {
    let splitFeature: Int
    let splitValue: Double
    var left: IsolationNode?
    var right: IsolationNode?
    let size: Int
    let isLeaf: Bool

    init(splitFeature: Int = 0, splitValue: Double = 0,
         left: IsolationNode? = nil, right: IsolationNode? = nil,
         size: Int = 0, isLeaf: Bool = false) {
        self.splitFeature = splitFeature
        self.splitValue = splitValue
        self.left = left
        self.right = right
        self.size = size
        self.isLeaf = isLeaf
    }
}

// MARK: - Isolation Forest

class IsolationForest {
    private let nTrees: Int
    private let maxSamples: Int
    private var trees: [IsolationNode] = []
    private var fitted = false

    init(nTrees: Int = 50, maxSamples: Int = 256) {
        self.nTrees = nTrees
        self.maxSamples = maxSamples
    }

    func fit(data: [[Double]]) {
        let n = min(data.count, maxSamples)
        let maxDepth = Int(ceil(log2(Double(n))))
        trees = (0..<nTrees).map { _ in
            let indices = (0..<data.count).shuffled().prefix(n)
            let sample = indices.map { data[$0] }
            return buildTree(data: sample, depth: 0, maxDepth: maxDepth)
        }
        fitted = true
    }

    private func buildTree(data: [[Double]], depth: Int, maxDepth: Int) -> IsolationNode {
        guard data.count > 1 && depth < maxDepth else {
            return IsolationNode(size: data.count, isLeaf: true)
        }

        let dim = data[0].count
        let feature = Int.random(in: 0..<dim)
        let values = data.map { $0[feature] }
        guard let minVal = values.min(), let maxVal = values.max(), minVal < maxVal else {
            return IsolationNode(size: data.count, isLeaf: true)
        }

        let splitVal = Double.random(in: minVal...maxVal)
        let leftData = data.filter { $0[feature] < splitVal }
        let rightData = data.filter { $0[feature] >= splitVal }

        return IsolationNode(
            splitFeature: feature,
            splitValue: splitVal,
            left: buildTree(data: leftData, depth: depth + 1, maxDepth: maxDepth),
            right: buildTree(data: rightData, depth: depth + 1, maxDepth: maxDepth),
            size: data.count
        )
    }

    private func pathLength(point: [Double], node: IsolationNode, depth: Int = 0) -> Double {
        guard !node.isLeaf else {
            return Double(depth) + cFunction(node.size)
        }
        if point[node.splitFeature] < node.splitValue {
            return pathLength(point: point, node: node.left!, depth: depth + 1)
        }
        return pathLength(point: point, node: node.right!, depth: depth + 1)
    }

    private func cFunction(_ n: Int) -> Double {
        guard n > 1 else { return 0 }
        let nf = Double(n)
        return 2.0 * (log(nf - 1.0) + 0.5772156649) - 2.0 * (nf - 1.0) / nf
    }

    func score(point: [Double]) -> Double {
        guard fitted else { return 0.5 }
        let avgPath = trees.map { pathLength(point: point, node: $0) }
            .reduce(0, +) / Double(trees.count)
        let cn = cFunction(maxSamples)
        return cn > 0 ? pow(2, -avgPath / cn) : 0.5
    }
}

// MARK: - IDS Engine

class IntrusionDetectionSystem {
    private let forest: IsolationForest
    private let threshold: Double
    private var packetLog: [NetworkPacket] = []
    private var alerts: [ThreatAlert] = []
    private var packetRates: [String: [Double]] = [:]
    private var alertCounter = 0
    private var trained = false

    init(threshold: Double = 0.7) {
        self.forest = IsolationForest(nTrees: 50)
        self.threshold = threshold
    }

    func train(normalTraffic: [[Double]]) {
        forest.fit(data: normalTraffic)
        trained = true
    }

    func analyzePacket(_ packet: NetworkPacket) -> ThreatAlert? {
        packetLog.append(packet)
        var rates = packetRates[packet.sourceId] ?? []
        rates.append(packet.timestamp)
        rates = rates.filter { packet.timestamp - $0 < 1.0 }
        packetRates[packet.sourceId] = rates

        // DoS detection
        if rates.count > 100 {
            return createAlert(.high, .dos, packet.sourceId,
                "DoS: \(rates.count) pkts/sec", 0.9, packet.timestamp)
        }

        // Unencrypted command
        if packet.packetType == "command" && !packet.isEncrypted {
            return createAlert(.medium, .injection, packet.sourceId,
                "Unencrypted command", 0.7, packet.timestamp)
        }

        // Anomaly detection
        if trained {
            let features = extractFeatures(packet)
            let score = forest.score(point: features)
            if score > threshold {
                return createAlert(.medium, .unknown, packet.sourceId,
                    "Anomaly: score=\(String(format: "%.3f", score))",
                    score, packet.timestamp)
            }
        }

        return nil
    }

    private func extractFeatures(_ packet: NetworkPacket) -> [Double] {
        let rate = Double(packetRates[packet.sourceId]?.count ?? 0)
        return [
            Double(packet.sizeBytes) / 1000.0,
            packet.isEncrypted ? 1.0 : 0.0,
            rate / 100.0,
            Double(packet.packetType.hashValue % 10) / 10.0,
            packet.timestamp.truncatingRemainder(dividingBy: 3600.0) / 3600.0
        ]
    }

    private func createAlert(_ level: ThreatLevel, _ attack: AttackType,
                             _ source: String, _ desc: String,
                             _ confidence: Double, _ timestamp: Double) -> ThreatAlert {
        alertCounter += 1
        let alert = ThreatAlert(
            alertId: String(format: "IDS-%06d", alertCounter),
            threatLevel: level, attackType: attack,
            sourceId: source, description: desc,
            confidence: confidence, timestamp: timestamp
        )
        alerts.append(alert)
        return alert
    }

    func summary() -> [String: Any] {
        var levelCounts: [String: Int] = [:]
        for alert in alerts {
            levelCounts[alert.threatLevel.rawValue, default: 0] += 1
        }
        return [
            "totalPackets": packetLog.count,
            "totalAlerts": alerts.count,
            "alertLevels": levelCounts,
            "trained": trained,
        ]
    }
}
