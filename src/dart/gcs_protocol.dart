// Phase 555 — GCS (Ground Control Station) Protocol in Dart
// Message types, command/telemetry protocol for swarm drone ATC.

import 'dart:convert';
import 'dart:typed_data';

// ── GCS Protocol version ──────────────────────────────────────────────────────

const String GCS_PROTOCOL_VERSION = '555';
const int    GCS_MAGIC_BYTE        = 0x55;
const int    GCS_MAX_PAYLOAD_BYTES = 1024;

// ── Message type enum ─────────────────────────────────────────────────────────

enum GcsMessageType {
  heartbeat,
  telemetry,
  commandArm,
  commandDisarm,
  commandTakeoff,
  commandLand,
  commandGoto,
  commandRtl,
  commandHold,
  missionUpload,
  missionAck,
  statusText,
  paramSet,
  paramGet,
  paramValue,
}

// ── Base GCS Message ──────────────────────────────────────────────────────────

/// Abstract base for all GCS Protocol messages.
/// Phase 555 — every Message carries a [type], [droneId], and [sequenceId].
abstract class GcsMessage {
  final GcsMessageType type;
  final String         droneId;
  final int            sequenceId;
  final DateTime       timestamp;

  const GcsMessage({
    required this.type,
    required this.droneId,
    required this.sequenceId,
    required this.timestamp,
  });

  Map<String, dynamic> toJson();

  @override
  String toString() =>
      'GcsMessage(type=${type.name}, drone=$droneId, seq=$sequenceId)';
}

// ── Telemetry Message ─────────────────────────────────────────────────────────

class TelemetryMessage extends GcsMessage {
  final double x, y, z;         // position metres
  final double vx, vy, vz;     // velocity m/s
  final double heading;         // degrees 0–360
  final double batteryPct;
  final String flightMode;

  const TelemetryMessage({
    required super.droneId,
    required super.sequenceId,
    required super.timestamp,
    required this.x,
    required this.y,
    required this.z,
    required this.vx,
    required this.vy,
    required this.vz,
    required this.heading,
    required this.batteryPct,
    required this.flightMode,
  }) : super(type: GcsMessageType.telemetry);

  @override
  Map<String, dynamic> toJson() => {
        'proto':    GCS_PROTOCOL_VERSION,
        'type':     type.name,
        'drone':    droneId,
        'seq':      sequenceId,
        'ts':       timestamp.millisecondsSinceEpoch,
        'pos':      [x, y, z],
        'vel':      [vx, vy, vz],
        'heading':  heading,
        'battery':  batteryPct,
        'mode':     flightMode,
      };
}

// ── Command Messages ──────────────────────────────────────────────────────────

class CommandMessage extends GcsMessage {
  final Map<String, dynamic> params;

  const CommandMessage({
    required super.type,
    required super.droneId,
    required super.sequenceId,
    required super.timestamp,
    this.params = const {},
  });

  @override
  Map<String, dynamic> toJson() => {
        'proto':  GCS_PROTOCOL_VERSION,
        'type':   type.name,
        'drone':  droneId,
        'seq':    sequenceId,
        'ts':     timestamp.millisecondsSinceEpoch,
        'params': params,
      };
}

// ── Protocol Encoder / Decoder ────────────────────────────────────────────────

/// Handles GCS Protocol framing: [MAGIC | LEN(2) | JSON_PAYLOAD | CRC(1)].
class GcsProtocol {
  static const String version = GCS_PROTOCOL_VERSION;

  /// Encode a [GcsMessage] to wire-format bytes.
  static Uint8List encode(GcsMessage msg) {
    final jsonBytes = utf8.encode(jsonEncode(msg.toJson()));
    final len       = jsonBytes.length;
    if (len > GCS_MAX_PAYLOAD_BYTES) {
      throw ArgumentError(
          '[555] GCS Protocol payload too large: $len > $GCS_MAX_PAYLOAD_BYTES');
    }

    final frame = BytesBuilder();
    frame.addByte(GCS_MAGIC_BYTE);
    frame.addByte((len >> 8) & 0xFF);
    frame.addByte(len & 0xFF);
    frame.add(jsonBytes);
    final crc = jsonBytes.fold<int>(0, (acc, b) => (acc ^ b) & 0xFF);
    frame.addByte(crc);
    return frame.toBytes();
  }

  /// Decode a [GcsMessage] from raw bytes. Returns null on framing error.
  static GcsMessage? decode(Uint8List frame) {
    if (frame.length < 4) return null;
    if (frame[0] != GCS_MAGIC_BYTE) return null;

    final len     = (frame[1] << 8) | frame[2];
    final payload = frame.sublist(3, 3 + len);
    final crc     = frame[3 + len];
    final calcCrc = payload.fold<int>(0, (acc, b) => (acc ^ b) & 0xFF);
    if (calcCrc != crc) return null;

    final jsonMap = jsonDecode(utf8.decode(payload)) as Map<String, dynamic>;
    return _fromJson(jsonMap);
  }

  static GcsMessage? _fromJson(Map<String, dynamic> m) {
    final typeStr  = m['type'] as String?;
    final droneId  = m['drone'] as String? ?? '';
    final seqId    = m['seq']   as int?    ?? 0;
    final ts       = DateTime.fromMillisecondsSinceEpoch(m['ts'] as int? ?? 0);

    switch (typeStr) {
      case 'telemetry':
        final pos = (m['pos'] as List).cast<num>();
        final vel = (m['vel'] as List).cast<num>();
        return TelemetryMessage(
          droneId:     droneId,
          sequenceId:  seqId,
          timestamp:   ts,
          x:           pos[0].toDouble(),
          y:           pos[1].toDouble(),
          z:           pos[2].toDouble(),
          vx:          vel[0].toDouble(),
          vy:          vel[1].toDouble(),
          vz:          vel[2].toDouble(),
          heading:     (m['heading'] as num).toDouble(),
          batteryPct:  (m['battery'] as num).toDouble(),
          flightMode:  m['mode'] as String? ?? 'UNKNOWN',
        );
      default:
        return null;
    }
  }
}

// ── Demo entry point ──────────────────────────────────────────────────────────

void main() {
  print('[555] GCS Protocol v$GCS_PROTOCOL_VERSION — Phase 555 demo');

  final telMsg = TelemetryMessage(
    droneId:    'DRONE-001',
    sequenceId: 1,
    timestamp:  DateTime.now(),
    x: 10.5, y: 20.3, z: 30.0,
    vx: 0.5,  vy: 0.2, vz: 0.0,
    heading:    45.0,
    batteryPct: 87.5,
    flightMode: 'AUTO',
  );

  final encoded = GcsProtocol.encode(telMsg);
  print('  Encoded ${encoded.length} bytes for ${telMsg.droneId}');

  final decoded = GcsProtocol.decode(encoded);
  print('  Decoded: $decoded');

  final cmdMsg = CommandMessage(
    type:       GcsMessageType.commandGoto,
    droneId:    'DRONE-001',
    sequenceId: 2,
    timestamp:  DateTime.now(),
    params:     {'x': 50.0, 'y': 50.0, 'z': 25.0},
  );
  print('  Command: ${cmdMsg.toJson()}');
}
