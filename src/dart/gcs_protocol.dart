// P555: GCSProtocol - Dart ground control station protocol
// Phase 555: GCS communication protocol for drone fleet management

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

enum MessageType {
  heartbeat,
  commandLong,
  setMode,
  requestDataStream,
  missionItem,
  missionCount,
  missionAck,
  statusText,
  attitude,
  globalPosition,
  batteryStatus,
  sysStatus,
}

class GCSMessage {
  final MessageType type;
  final int systemId;
  final int componentId;
  final int sequenceNumber;
  final Map<String, dynamic> payload;

  const GCSMessage({
    required this.type,
    required this.systemId,
    required this.componentId,
    required this.sequenceNumber,
    required this.payload,
  });

  factory GCSMessage.heartbeat(int sysId, int compId, int seq) => GCSMessage(
    type: MessageType.heartbeat,
    systemId: sysId,
    componentId: compId,
    sequenceNumber: seq,
    payload: {'type': 'QUADROTOR', 'autopilot': 'ARDUPILOTMEGA', 'base_mode': 0},
  );

  factory GCSMessage.commandLong({
    required int sysId,
    required int seq,
    required int command,
    Map<String, double> params = const {},
  }) => GCSMessage(
    type: MessageType.commandLong,
    systemId: sysId,
    componentId: 0,
    sequenceNumber: seq,
    payload: {'command': command, 'params': params},
  );

  Map<String, dynamic> toJson() => {
    'type': type.name,
    'system_id': systemId,
    'component_id': componentId,
    'sequence': sequenceNumber,
    'payload': payload,
  };

  @override
  String toString() => jsonEncode(toJson());
}

class Protocol {
  final String host;
  final int port;
  int _sequence = 0;

  Protocol({required this.host, required this.port});

  int get nextSequence => _sequence++;

  GCSMessage buildHeartbeat(int systemId) =>
    GCSMessage.heartbeat(systemId, 0, nextSequence);

  GCSMessage buildTakeoffCommand(int systemId, double altitude) =>
    GCSMessage.commandLong(
      sysId: systemId,
      seq: nextSequence,
      command: 22,
      params: {'altitude': altitude},
    );

  GCSMessage buildLandCommand(int systemId) =>
    GCSMessage.commandLong(
      sysId: systemId,
      seq: nextSequence,
      command: 21,
    );

  GCSMessage buildGotoCommand(int systemId, double lat, double lon, double alt) =>
    GCSMessage.commandLong(
      sysId: systemId,
      seq: nextSequence,
      command: 192,
      params: {'lat': lat, 'lon': lon, 'alt': alt},
    );

  String encodeMessage(GCSMessage msg) => jsonEncode(msg.toJson());

  GCSMessage? decodeMessage(String data) {
    try {
      final json = jsonDecode(data) as Map<String, dynamic>;
      final type = MessageType.values.firstWhere(
        (t) => t.name == json['type'],
        orElse: () => MessageType.statusText,
      );
      return GCSMessage(
        type: type,
        systemId: json['system_id'] as int,
        componentId: json['component_id'] as int,
        sequenceNumber: json['sequence'] as int,
        payload: json['payload'] as Map<String, dynamic>,
      );
    } catch (_) {
      return null;
    }
  }
}
