// Phase 555: GCS Protocol — Dart
// SDACS Ground Control Station communication protocol implementation

// Phase 555 marker — GCS Protocol and Message handling

import 'dart:typed_data';
import 'dart:convert';
import 'dart:math';

// ============================================================
// Message types

enum MessageType {
  heartbeat,
  command,
  telemetry,
  acknowledgment,
  alert,
  missionItem,
  missionAck,
  paramRequest,
  paramValue,
}

// ============================================================
// Protocol: GCS binary message frame

class ProtocolFrame {
  static const int MAGIC    = 0xFE;
  static const int HEADER_SIZE = 8;

  final int sequenceNum;
  final String systemId;
  final MessageType type;
  final Uint8List payload;
  final int checksum;

  const ProtocolFrame({
    required this.sequenceNum,
    required this.systemId,
    required this.type,
    required this.payload,
    required this.checksum,
  });

  factory ProtocolFrame.create({
    required int seqNum,
    required String systemId,
    required MessageType type,
    required Uint8List payload,
  }) {
    final checksum = _computeChecksum(payload);
    return ProtocolFrame(
      sequenceNum: seqNum,
      systemId:    systemId,
      type:        type,
      payload:     payload,
      checksum:    checksum,
    );
  }

  Uint8List encode() {
    final buf = ByteData(HEADER_SIZE + payload.length + 2);
    int offset = 0;
    buf.setUint8(offset++, MAGIC);
    buf.setUint8(offset++, payload.length);
    buf.setUint16(offset, sequenceNum, Endian.little); offset += 2;
    buf.setUint8(offset++, type.index);
    // System ID (first 3 bytes)
    final sysBytes = utf8.encode(systemId.padRight(3).substring(0, 3));
    for (final b in sysBytes) buf.setUint8(offset++, b);

    for (int i = 0; i < payload.length; i++) {
      buf.setUint8(HEADER_SIZE + i, payload[i]);
    }
    buf.setUint16(HEADER_SIZE + payload.length, checksum, Endian.little);
    return buf.buffer.asUint8List();
  }

  static int _computeChecksum(Uint8List data) {
    int crc = 0xFFFF;
    for (final byte in data) {
      crc ^= byte;
      for (int i = 0; i < 8; i++) {
        if (crc & 0x0001 != 0) {
          crc = (crc >> 1) ^ 0x8408;
        } else {
          crc >>= 1;
        }
      }
    }
    return crc ^ 0xFFFF;
  }

  bool verifyChecksum() => _computeChecksum(payload) == checksum;

  @override
  String toString() =>
    'Frame(seq=$sequenceNum sys=$systemId type=${type.name} len=${payload.length})';
}

// ============================================================
// Message builders

class GCSMessages {
  static Uint8List heartbeatPayload(String droneId, String mode, double battery) {
    final data = <int>[
      ...utf8.encode(droneId.padRight(8).substring(0, 8)),
      ...utf8.encode(mode.padRight(8).substring(0, 8)),
      ..._float32Bytes(battery),
    ];
    return Uint8List.fromList(data);
  }

  static Uint8List telemetryPayload({
    required double lat, required double lon,
    required double alt, required double speed,
    required double heading, required double battery,
  }) {
    final buf = ByteData(6 * 4);
    buf.setFloat32(0,  lat,     Endian.little);
    buf.setFloat32(4,  lon,     Endian.little);
    buf.setFloat32(8,  alt,     Endian.little);
    buf.setFloat32(12, speed,   Endian.little);
    buf.setFloat32(16, heading, Endian.little);
    buf.setFloat32(20, battery, Endian.little);
    return buf.buffer.asUint8List();
  }

  static Uint8List commandPayload(String command, Map<String, double> params) {
    final json = jsonEncode({'cmd': command, 'params': params});
    return Uint8List.fromList(utf8.encode(json));
  }

  static List<int> _float32Bytes(double value) {
    final buf = ByteData(4);
    buf.setFloat32(0, value, Endian.little);
    return buf.buffer.asUint8List().toList();
  }
}

// ============================================================
// GCS Protocol handler

class GCSProtocol {
  final String gcsId;
  int _sequenceNum = 0;
  final List<ProtocolFrame> _sentLog  = [];
  final List<ProtocolFrame> _recvLog  = [];
  final Map<int, DateTime>  _pendingAcks = {};

  GCSProtocol({required this.gcsId});

  ProtocolFrame buildFrame(MessageType type, Uint8List payload) {
    final frame = ProtocolFrame.create(
      seqNum:   _sequenceNum++,
      systemId: gcsId,
      type:     type,
      payload:  payload,
    );
    _sentLog.add(frame);
    if (type == MessageType.command) {
      _pendingAcks[frame.sequenceNum] = DateTime.now();
    }
    return frame;
  }

  void receive(ProtocolFrame frame) {
    if (!frame.verifyChecksum()) {
      throw FormatException('Checksum mismatch for frame ${frame.sequenceNum}');
    }
    _recvLog.add(frame);
    if (frame.type == MessageType.acknowledgment) {
      _pendingAcks.remove(frame.sequenceNum);
    }
  }

  Map<String, dynamic> stats() => {
    'gcs_id':       gcsId,
    'sent':         _sentLog.length,
    'received':     _recvLog.length,
    'pending_acks': _pendingAcks.length,
    'sequence':     _sequenceNum,
  };
}

// Demo
void main() {
  final gcs = GCSProtocol(gcsId: 'GCS-001');

  final hbPayload = GCSMessages.heartbeatPayload('D001', 'AUTO', 75.0);
  final hbFrame   = gcs.buildFrame(MessageType.heartbeat, hbPayload);
  print('Phase 555: GCS Protocol — $hbFrame');

  final telPayload = GCSMessages.telemetryPayload(
    lat: 37.5665, lon: 126.978, alt: 60.0, speed: 10.0, heading: 90.0, battery: 75.0,
  );
  final telFrame = gcs.buildFrame(MessageType.telemetry, telPayload);
  print('Telemetry frame: $telFrame');
  print('Checksum valid: ${telFrame.verifyChecksum()}');
  print('Stats: ${gcs.stats()}');
}
