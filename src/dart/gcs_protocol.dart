// Phase 555: gcs_protocol — Dart/Flutter 기반 GCS 통신 프로토콜
// SDACS Ground Control Station Protocol Implementation

import 'dart:convert';
import 'dart:typed_data';

// GCS 메시지 타입 열거형
enum MessageType {
  telemetry,
  command,
  acknowledge,
  heartbeat,
  alert,
  statusRequest,
  statusResponse,
}

// GCS 프로토콜 메시지 기반 클래스
abstract class GcsMessage {
  final MessageType type;
  final int droneId;
  final int sequenceNumber;
  final DateTime timestamp;

  const GcsMessage({
    required this.type,
    required this.droneId,
    required this.sequenceNumber,
    required this.timestamp,
  });

  Map<String, dynamic> toJson();

  String serialize() => jsonEncode(toJson());
}

// 텔레메트리 Message
class TelemetryMessage extends GcsMessage {
  final double latitude;
  final double longitude;
  final double altitude;
  final double batteryPercent;
  final double speedMs;
  final String flightMode;
  final bool isArmed;

  const TelemetryMessage({
    required super.droneId,
    required super.sequenceNumber,
    required super.timestamp,
    required this.latitude,
    required this.longitude,
    required this.altitude,
    required this.batteryPercent,
    required this.speedMs,
    required this.flightMode,
    required this.isArmed,
  }) : super(type: MessageType.telemetry);

  @override
  Map<String, dynamic> toJson() => {
    'type': 'telemetry',
    'drone_id': droneId,
    'seq': sequenceNumber,
    'ts': timestamp.millisecondsSinceEpoch,
    'lat': latitude,
    'lon': longitude,
    'alt': altitude,
    'battery': batteryPercent,
    'speed': speedMs,
    'mode': flightMode,
    'armed': isArmed,
  };

  factory TelemetryMessage.fromJson(Map<String, dynamic> json) {
    return TelemetryMessage(
      droneId: json['drone_id'] as int,
      sequenceNumber: json['seq'] as int,
      timestamp: DateTime.fromMillisecondsSinceEpoch(json['ts'] as int),
      latitude: (json['lat'] as num).toDouble(),
      longitude: (json['lon'] as num).toDouble(),
      altitude: (json['alt'] as num).toDouble(),
      batteryPercent: (json['battery'] as num).toDouble(),
      speedMs: (json['speed'] as num).toDouble(),
      flightMode: json['mode'] as String,
      isArmed: json['armed'] as bool,
    );
  }
}

// 명령 Message
class CommandMessage extends GcsMessage {
  final String command;
  final Map<String, dynamic> parameters;

  const CommandMessage({
    required super.droneId,
    required super.sequenceNumber,
    required super.timestamp,
    required this.command,
    this.parameters = const {},
  }) : super(type: MessageType.command);

  @override
  Map<String, dynamic> toJson() => {
    'type': 'command',
    'drone_id': droneId,
    'seq': sequenceNumber,
    'ts': timestamp.millisecondsSinceEpoch,
    'cmd': command,
    'params': parameters,
  };
}

// 확인 응답 Message
class AcknowledgeMessage extends GcsMessage {
  final int acknowledgedSeq;
  final bool success;
  final String? errorMessage;

  const AcknowledgeMessage({
    required super.droneId,
    required super.sequenceNumber,
    required super.timestamp,
    required this.acknowledgedSeq,
    required this.success,
    this.errorMessage,
  }) : super(type: MessageType.acknowledge);

  @override
  Map<String, dynamic> toJson() => {
    'type': 'ack',
    'drone_id': droneId,
    'seq': sequenceNumber,
    'ts': timestamp.millisecondsSinceEpoch,
    'ack_seq': acknowledgedSeq,
    'success': success,
    if (errorMessage != null) 'error': errorMessage,
  };
}

// GCS Protocol 핸들러
class GcsProtocol {
  final int groundStationId;
  int _sequenceCounter = 0;

  GcsProtocol({required this.groundStationId});

  // 다음 시퀀스 번호 발급
  int get nextSequence => ++_sequenceCounter;

  // 명령 메시지 생성
  CommandMessage createCommand(int droneId, String command, {Map<String, dynamic>? params}) {
    return CommandMessage(
      droneId: droneId,
      sequenceNumber: nextSequence,
      timestamp: DateTime.now(),
      command: command,
      parameters: params ?? {},
    );
  }

  // 메시지 파싱
  GcsMessage? parseMessage(String json) {
    try {
      final data = jsonDecode(json) as Map<String, dynamic>;
      final type = data['type'] as String?;
      return switch (type) {
        'telemetry' => TelemetryMessage.fromJson(data),
        _ => null,
      };
    } catch (e) {
      return null;
    }
  }

  // 바이너리 직렬화 (간단 구현)
  Uint8List serializeBinary(GcsMessage msg) {
    final jsonStr = msg.serialize();
    final bytes = utf8.encode(jsonStr);
    final buffer = ByteData(4 + bytes.length);
    buffer.setUint32(0, bytes.length, Endian.big);
    final result = Uint8List(4 + bytes.length);
    result.setRange(0, 4, buffer.buffer.asUint8List());
    result.setRange(4, 4 + bytes.length, bytes);
    return result;
  }
}

void main() {
  print('SDACS GCS Protocol Module — Phase 555');
  final protocol = GcsProtocol(groundStationId: 0);

  final cmd = protocol.createCommand(1, 'TAKEOFF', params: {'alt': 50.0});
  print('Command: ${cmd.serialize()}');

  final telemetry = TelemetryMessage(
    droneId: 1,
    sequenceNumber: 1,
    timestamp: DateTime.now(),
    latitude: 37.5,
    longitude: 127.0,
    altitude: 50.0,
    batteryPercent: 85.0,
    speedMs: 5.0,
    flightMode: 'GUIDED',
    isArmed: true,
  );
  print('Telemetry: ${telemetry.serialize()}');
}
