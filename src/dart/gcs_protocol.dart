// Phase 555: Dart Mobile GCS Protocol
// 모바일 지상 통제소 프로토콜: MAVLink 유사 메시지 직렬화, 명령 큐, 텔레메트리 파싱

import 'dart:math';

class PRNG {
  int state;
  PRNG(int seed) : state = seed ^ 0x6c62272e;

  int next() {
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return state.abs();
  }

  double uniform() => (next() % 10000) / 10000.0;
}

enum MessageType { heartbeat, position, command, telemetry, alert }

class GCSMessage {
  final int seqId;
  final String sourceId;
  final String targetId;
  final MessageType type;
  final Map<String, dynamic> payload;
  final int timestamp;

  GCSMessage(this.seqId, this.sourceId, this.targetId, this.type, this.payload, this.timestamp);

  List<int> serialize() {
    // Simple binary-like representation
    final bytes = <int>[];
    bytes.add(0xFE); // start marker
    bytes.add(seqId & 0xFF);
    bytes.add(type.index);
    bytes.add(timestamp & 0xFF);
    bytes.add((timestamp >> 8) & 0xFF);
    bytes.add(0xAA); // end marker
    return bytes;
  }

  static GCSMessage? deserialize(List<int> bytes) {
    if (bytes.isEmpty || bytes[0] != 0xFE) return null;
    return GCSMessage(bytes[1], "unknown", "gcs", MessageType.values[bytes[2] % MessageType.values.length],
        {}, bytes[3] | (bytes[4] << 8));
  }
}

class CommandQueue {
  final List<GCSMessage> _queue = [];
  int _processed = 0;

  void enqueue(GCSMessage msg) => _queue.add(msg);

  GCSMessage? dequeue() {
    if (_queue.isEmpty) return null;
    _processed++;
    return _queue.removeAt(0);
  }

  int get length => _queue.length;
  int get processed => _processed;
}

class TelemetryParser {
  int packetsReceived = 0;
  int parseErrors = 0;

  Map<String, double>? parse(GCSMessage msg) {
    packetsReceived++;
    if (msg.type != MessageType.telemetry) {
      parseErrors++;
      return null;
    }
    return {
      'battery': (msg.payload['battery'] ?? 0.0).toDouble(),
      'altitude': (msg.payload['altitude'] ?? 0.0).toDouble(),
      'speed': (msg.payload['speed'] ?? 0.0).toDouble(),
      'heading': (msg.payload['heading'] ?? 0.0).toDouble(),
    };
  }
}

class GCSProtocol {
  final int nDrones;
  final PRNG rng;
  final CommandQueue commandQueue = CommandQueue();
  final TelemetryParser parser = TelemetryParser();
  int seqCounter = 0;
  int alertCount = 0;

  GCSProtocol(this.nDrones, int seed) : rng = PRNG(seed);

  GCSMessage createHeartbeat(String droneId) {
    seqCounter++;
    return GCSMessage(seqCounter, droneId, "gcs", MessageType.heartbeat, {}, seqCounter * 100);
  }

  GCSMessage createTelemetry(String droneId) {
    seqCounter++;
    return GCSMessage(seqCounter, droneId, "gcs", MessageType.telemetry, {
      'battery': 50.0 + rng.uniform() * 50,
      'altitude': 30.0 + rng.uniform() * 70,
      'speed': rng.uniform() * 20,
      'heading': rng.uniform() * 360,
    }, seqCounter * 100);
  }

  GCSMessage createCommand(String targetDrone, String action) {
    seqCounter++;
    return GCSMessage(seqCounter, "gcs", targetDrone, MessageType.command, {'action': action}, seqCounter * 100);
  }

  void simulate(int steps) {
    for (var step = 0; step < steps; step++) {
      for (var i = 0; i < nDrones; i++) {
        final droneId = 'drone_$i';
        // Send heartbeat
        createHeartbeat(droneId);
        // Send telemetry
        final telem = createTelemetry(droneId);
        final parsed = parser.parse(telem);
        // Check alerts
        if (parsed != null && parsed['battery']! < 60) {
          alertCount++;
          commandQueue.enqueue(createCommand(droneId, 'return_to_base'));
        }
        // Process commands
        commandQueue.dequeue();
      }
    }
  }

  Map<String, dynamic> summary() => {
    'drones': nDrones,
    'messages_sent': seqCounter,
    'telemetry_received': parser.packetsReceived,
    'alerts': alertCount,
    'commands_processed': commandQueue.processed,
  };
}

void main() {
  final gcs = GCSProtocol(10, 42);
  gcs.simulate(20);
  final s = gcs.summary();
  s.forEach((k, v) => print('  $k: $v'));
}
