// Phase 555 — GCS Protocol with Message Types
// Dart module implementing the Ground Control Station communication protocol.

// ===== Enumerations =====

/// Message type identifiers for the GCS protocol
enum MessageType {
  telemetry,
  command,
  heartbeat,
  alert,
  acknowledgement,
  statusRequest,
  missionUpdate,
}

/// Command types supported by the GCS Protocol
enum CommandType {
  takeoff,
  land,
  move,
  returnToLaunch,
  hold,
  setSpeed,
  setAltitude,
  emergencyStop,
}

/// Alert severity levels
enum AlertSeverity { info, warning, critical }

// ===== Message Base Class =====

/// Base class for all GCS Protocol messages
abstract class Message {
  final String messageId;
  final String senderId;
  final String recipientId;
  final DateTime timestamp;
  final MessageType type;

  Message({
    required this.messageId,
    required this.senderId,
    required this.recipientId,
    required this.type,
  }) : timestamp = DateTime.now();

  Map<String, dynamic> toJson();
}

// ===== Concrete Message Types =====

/// Telemetry message from drone to GCS
class TelemetryMessage extends Message {
  final double x;
  final double y;
  final double z;
  final double vx;
  final double vy;
  final double vz;
  final double battery;
  final double signalStrength;

  TelemetryMessage({
    required String messageId,
    required String droneId,
    required String gcsId,
    required this.x,
    required this.y,
    required this.z,
    required this.vx,
    required this.vy,
    required this.vz,
    required this.battery,
    required this.signalStrength,
  }) : super(
          messageId: messageId,
          senderId: droneId,
          recipientId: gcsId,
          type: MessageType.telemetry,
        );

  @override
  Map<String, dynamic> toJson() => {
        'id': messageId,
        'type': 'telemetry',
        'drone': senderId,
        'pos': {'x': x, 'y': y, 'z': z},
        'vel': {'vx': vx, 'vy': vy, 'vz': vz},
        'battery': battery,
        'signal': signalStrength,
      };
}

/// Command message from GCS to drone
class CommandMessage extends Message {
  final CommandType command;
  final Map<String, double> parameters;

  CommandMessage({
    required String messageId,
    required String gcsId,
    required String droneId,
    required this.command,
    this.parameters = const {},
  }) : super(
          messageId: messageId,
          senderId: gcsId,
          recipientId: droneId,
          type: MessageType.command,
        );

  @override
  Map<String, dynamic> toJson() => {
        'id': messageId,
        'type': 'command',
        'command': command.name,
        'params': parameters,
      };
}

/// Heartbeat message to verify link health
class HeartbeatMessage extends Message {
  final int sequenceNumber;
  final double systemLoad;

  HeartbeatMessage({
    required String messageId,
    required String senderId,
    required String recipientId,
    required this.sequenceNumber,
    this.systemLoad = 0.0,
  }) : super(
          messageId: messageId,
          senderId: senderId,
          recipientId: recipientId,
          type: MessageType.heartbeat,
        );

  @override
  Map<String, dynamic> toJson() => {
        'id': messageId,
        'type': 'heartbeat',
        'seq': sequenceNumber,
        'load': systemLoad,
      };
}

/// Alert message for safety and operational notifications
class AlertMessage extends Message {
  final String alertCode;
  final AlertSeverity severity;
  final String description;

  AlertMessage({
    required String messageId,
    required String senderId,
    required String recipientId,
    required this.alertCode,
    required this.severity,
    required this.description,
  }) : super(
          messageId: messageId,
          senderId: senderId,
          recipientId: recipientId,
          type: MessageType.alert,
        );

  @override
  Map<String, dynamic> toJson() => {
        'id': messageId,
        'type': 'alert',
        'code': alertCode,
        'severity': severity.name,
        'description': description,
      };
}

// ===== GCS Protocol Handler =====

/// The GCS Protocol class handles message routing and validation
class GCSProtocol {
  final String gcsId;
  final List<Message> messageLog = [];
  int _messageCounter = 0;

  GCSProtocol(this.gcsId);

  String _nextId() => 'MSG-${++_messageCounter}';

  /// Create a command message for a specific drone
  CommandMessage createCommand(String droneId, CommandType cmd,
      [Map<String, double> params = const {}]) {
    final msg = CommandMessage(
      messageId: _nextId(),
      gcsId: gcsId,
      droneId: droneId,
      command: cmd,
      parameters: params,
    );
    messageLog.add(msg);
    return msg;
  }

  /// Process an incoming message from a drone
  void receive(Message msg) {
    messageLog.add(msg);
    switch (msg.type) {
      case MessageType.telemetry:
        _handleTelemetry(msg as TelemetryMessage);
        break;
      case MessageType.alert:
        _handleAlert(msg as AlertMessage);
        break;
      default:
        break;
    }
  }

  void _handleTelemetry(TelemetryMessage t) {
    if (t.battery < 20.0) {
      print('GCS: LOW BATTERY on ${t.senderId}: ${t.battery}%');
    }
  }

  void _handleAlert(AlertMessage a) {
    print('GCS ALERT [${a.severity.name}]: ${a.alertCode} - ${a.description}');
  }

  Map<String, dynamic> stats() => {
        'gcs_id': gcsId,
        'total_messages': messageLog.length,
        'phase': '555',
      };
}

// ===== Main =====
void main() {
  print('Phase 555: GCS Protocol with Message Types');
  final gcs = GCSProtocol('GCS-MAIN');

  final cmd = gcs.createCommand('D001', CommandType.takeoff, {'altitude': 50.0});
  print('Command sent: ${cmd.toJson()}');

  final tel = TelemetryMessage(
    messageId: 'TEL-001',
    droneId: 'D001',
    gcsId: 'GCS-MAIN',
    x: 10.0, y: 5.0, z: 50.0,
    vx: 1.0, vy: 0.5, vz: 0.0,
    battery: 85.0,
    signalStrength: -65.0,
  );
  gcs.receive(tel);
  print('Stats: ${gcs.stats()}');
}
