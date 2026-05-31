// gcs_protocol.dart - Ground Control Station protocol for SDACS (Phase 555)
// Dart implementation of GCS communication protocol

import 'dart:typed_data';
import 'dart:convert';

// GCS message types
enum MessageType {
  telemetry,
  command,
  heartbeat,
  conflictAlert,
  statusRequest,
  statusResponse,
}

// Base GCS Message structure
abstract class Message {
  final String messageId;
  final String droneId;
  final MessageType type;
  final DateTime timestamp;

  const Message({
    required this.messageId,
    required this.droneId,
    required this.type,
    required this.timestamp,
  });

  Map<String, dynamic> toJson();
}

// Telemetry message from drone to GCS
class TelemetryMessage extends Message {
  final double latitude;
  final double longitude;
  final double altitude;
  final double velocityX;
  final double velocityY;
  final double velocityZ;
  final int battery;
  final String status;

  const TelemetryMessage({
    required super.messageId,
    required super.droneId,
    required super.timestamp,
    required this.latitude,
    required this.longitude,
    required this.altitude,
    required this.velocityX,
    required this.velocityY,
    required this.velocityZ,
    required this.battery,
    required this.status,
  }) : super(type: MessageType.telemetry);

  @override
  Map<String, dynamic> toJson() => {
    'messageId': messageId,
    'droneId':   droneId,
    'type':      'telemetry',
    'timestamp': timestamp.toIso8601String(),
    'latitude':  latitude,
    'longitude': longitude,
    'altitude':  altitude,
    'battery':   battery,
    'status':    status,
  };
}

// Command from GCS to drone
class CommandMessage extends Message {
  final String command;
  final Map<String, dynamic> params;

  const CommandMessage({
    required super.messageId,
    required super.droneId,
    required super.timestamp,
    required this.command,
    this.params = const {},
  }) : super(type: MessageType.command);

  @override
  Map<String, dynamic> toJson() => {
    'messageId': messageId,
    'droneId':   droneId,
    'type':      'command',
    'command':   command,
    'params':    params,
  };
}

// GCS Protocol handler
class GCSProtocol {
  static const int PROTOCOL_VERSION = 2;
  static const int MAX_PACKET_SIZE = 1024;
  static const String MAGIC_HEADER = "SDACS";

  final String stationId;
  int sequenceNumber = 0;
  final List<Message> messageLog = [];

  GCSProtocol(this.stationId);

  // Serialize message to binary packet
  Uint8List encode(Message msg) {
    final json = jsonEncode(msg.toJson());
    final bytes = utf8.encode(json);
    final packet = BytesBuilder();
    packet.add(utf8.encode(MAGIC_HEADER));
    packet.addByte(PROTOCOL_VERSION);
    packet.addByte(sequenceNumber++ & 0xFF);
    packet.add(bytes);
    return packet.toBytes();
  }

  // Decode binary packet to message
  Map<String, dynamic>? decode(Uint8List data) {
    final magic = utf8.decode(data.sublist(0, 5));
    if (magic != MAGIC_HEADER) return null;
    try {
      final json = utf8.decode(data.sublist(7));
      return jsonDecode(json) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  void logMessage(Message msg) {
    messageLog.add(msg);
  }

  Map<String, dynamic> getStats() => {
    'stationId': stationId,
    'version':   PROTOCOL_VERSION,
    'messages':  messageLog.length,
    'sequence':  sequenceNumber,
  };
}
