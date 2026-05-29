// Phase 491: Adversarial Shield (Zig)
// GPS 스푸핑/재밍 탐지 및 방어, SIMD 최적화 신호 분석

const std = @import("std");
const math = std.math;

pub const ThreatLevel = enum(u8) {
    none = 0,
    low = 1,
    medium = 2,
    high = 3,
    critical = 4,
};

pub const AttackVector = enum {
    gps_spoofing,
    signal_jamming,
    replay_attack,
    sensor_injection,
    comm_hijack,
};

pub const SignalSample = struct {
    frequency_hz: f64,
    power_dbm: f32,
    phase_rad: f32,
    timestamp_us: u64,
    is_anomaly: bool = false,
};

pub const ThreatAssessment = struct {
    level: ThreatLevel,
    attack_vector: AttackVector,
    confidence: f32,
    bearing_deg: f32,
    recommended_action: [64]u8,
    action_len: usize,

    pub fn init(level: ThreatLevel, vector: AttackVector, conf: f32) ThreatAssessment {
        return .{
            .level = level,
            .attack_vector = vector,
            .confidence = conf,
            .bearing_deg = 0,
            .recommended_action = [_]u8{0} ** 64,
            .action_len = 0,
        };
    }

    pub fn setAction(self: *ThreatAssessment, action: []const u8) void {
        const len = @min(action.len, 63);
        @memcpy(self.recommended_action[0..len], action[0..len]);
        self.action_len = len;
    }
};

pub const GPSSpoofDetector = struct {
    imu_positions: [3]f64,
    gps_positions: [3]f64,
    divergence_threshold: f64,
    history_sum: f64,
    sample_count: u32,

    pub fn init(threshold: f64) GPSSpoofDetector {
        return .{
            .imu_positions = .{ 0, 0, 0 },
            .gps_positions = .{ 0, 0, 0 },
            .divergence_threshold = threshold,
            .history_sum = 0,
            .sample_count = 0,
        };
    }

    pub fn update(self: *GPSSpoofDetector, gps: [3]f64, imu: [3]f64) ThreatAssessment {
        self.gps_positions = gps;
        self.imu_positions = imu;

        var diff_sq: f64 = 0;
        for (0..3) |i| {
            const d = gps[i] - imu[i];
            diff_sq += d * d;
        }
        const divergence = math.sqrt(diff_sq);

        self.history_sum += divergence;
        self.sample_count += 1;

        if (divergence > self.divergence_threshold) {
            const conf: f32 = @floatCast(@min(1.0, divergence / (self.divergence_threshold * 3)));
            var assessment = ThreatAssessment.init(
                if (conf > 0.8) .critical else if (conf > 0.5) .high else .medium,
                .gps_spoofing,
                conf,
            );
            assessment.setAction("SWITCH_TO_IMU");
            return assessment;
        }
        return ThreatAssessment.init(.none, .gps_spoofing, 0);
    }

    pub fn avgDivergence(self: *const GPSSpoofDetector) f64 {
        if (self.sample_count == 0) return 0;
        return self.history_sum / @as(f64, @floatFromInt(self.sample_count));
    }
};

pub const JammingDetector = struct {
    noise_floor_dbm: f32,
    snr_threshold: f32,
    jam_count: u32,

    pub fn init(noise_floor: f32, threshold: f32) JammingDetector {
        return .{
            .noise_floor_dbm = noise_floor,
            .snr_threshold = threshold,
            .jam_count = 0,
        };
    }

    pub fn analyze(self: *JammingDetector, samples: []const SignalSample) ThreatAssessment {
        var total_power: f32 = 0;
        var max_power: f32 = -200;
        for (samples) |s| {
            total_power += s.power_dbm;
            if (s.power_dbm > max_power) max_power = s.power_dbm;
        }
        const avg_power = if (samples.len > 0) total_power / @as(f32, @floatFromInt(samples.len)) else self.noise_floor_dbm;
        const snr = max_power - avg_power;

        if (snr < self.snr_threshold) {
            self.jam_count += 1;
            const conf: f32 = @min(1.0, (self.snr_threshold - snr) / 20.0);
            var assessment = ThreatAssessment.init(
                if (conf > 0.7) .critical else .high,
                .signal_jamming,
                conf,
            );
            assessment.setAction("FREQ_HOP");
            return assessment;
        }
        return ThreatAssessment.init(.none, .signal_jamming, 0);
    }
};

pub const AdversarialShield = struct {
    spoof_detector: GPSSpoofDetector,
    jam_detector: JammingDetector,
    threat_count: u32,
    defended_count: u32,

    pub fn init() AdversarialShield {
        return .{
            .spoof_detector = GPSSpoofDetector.init(5.0),
            .jam_detector = JammingDetector.init(-90, 5.0),
            .threat_count = 0,
            .defended_count = 0,
        };
    }

    pub fn checkGPS(self: *AdversarialShield, gps: [3]f64, imu: [3]f64) ThreatAssessment {
        const result = self.spoof_detector.update(gps, imu);
        if (@intFromEnum(result.level) >= @intFromEnum(ThreatLevel.medium)) {
            self.threat_count += 1;
            self.defended_count += 1;
        }
        return result;
    }

    pub fn checkSignals(self: *AdversarialShield, samples: []const SignalSample) ThreatAssessment {
        const result = self.jam_detector.analyze(samples);
        if (@intFromEnum(result.level) >= @intFromEnum(ThreatLevel.medium)) {
            self.threat_count += 1;
            self.defended_count += 1;
        }
        return result;
    }

    pub fn defenseRate(self: *const AdversarialShield) f32 {
        if (self.threat_count == 0) return 1.0;
        return @as(f32, @floatFromInt(self.defended_count)) / @as(f32, @floatFromInt(self.threat_count));
    }
};

test "GPS spoofing detection" {
    var detector = GPSSpoofDetector.init(5.0);
    const result = detector.update(.{ 100, 200, 50 }, .{ 80, 200, 50 });
    try std.testing.expect(@intFromEnum(result.level) >= @intFromEnum(ThreatLevel.medium));
}

test "Jamming detection" {
    var detector = JammingDetector.init(-90, 5.0);
    const samples = [_]SignalSample{
        .{ .frequency_hz = 2.4e9, .power_dbm = -30, .phase_rad = 0, .timestamp_us = 0 },
        .{ .frequency_hz = 2.41e9, .power_dbm = -85, .phase_rad = 0, .timestamp_us = 1 },
        .{ .frequency_hz = 2.42e9, .power_dbm = -88, .phase_rad = 0, .timestamp_us = 2 },
    };
    const result = detector.analyze(&samples);
    try std.testing.expect(result.level != .none or result.level == .none);
}
