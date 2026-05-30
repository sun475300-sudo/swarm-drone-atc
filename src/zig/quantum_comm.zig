// Phase 521: quantum_comm — Zig 기반 양자 통신 시뮬레이터
// SDACS Quantum Communication Module (BB84 Protocol)

const std = @import("std");
const math = std.math;

// BB84 양자 키 분배 프로토콜 구현
pub const QubitBasis = enum { rectilinear, diagonal };
pub const QubitState = enum { zero, one };

pub const Qubit = struct {
    state: QubitState,
    basis: QubitBasis,
};

// PRNG 기반 양자 측정 시뮬레이션
pub const QuantumPRNG = struct {
    seed: u64,
    state: u64,

    pub fn init(seed: u64) QuantumPRNG {
        return .{ .seed = seed, .state = seed ^ 0x12345678ABCDEF90 };
    }

    pub fn next(self: *QuantumPRNG) u64 {
        // xorshift64 PRNG
        self.state ^= self.state << 13;
        self.state ^= self.state >> 7;
        self.state ^= self.state << 17;
        return self.state;
    }

    pub fn nextBool(self: *QuantumPRNG) bool {
        return (self.next() & 1) == 1;
    }
};

pub const BB84Channel = struct {
    prng: QuantumPRNG,
    error_rate: f64,
    key_bits: std.ArrayList(u1),

    pub fn init(allocator: std.mem.Allocator, seed: u64, error_rate: f64) BB84Channel {
        return .{
            .prng = QuantumPRNG.init(seed),
            .error_rate = error_rate,
            .key_bits = std.ArrayList(u1).init(allocator),
        };
    }

    pub fn deinit(self: *BB84Channel) void {
        self.key_bits.deinit();
    }

    // Alice가 qubit 전송
    pub fn alicePrepare(self: *BB84Channel) Qubit {
        return .{
            .state = if (self.prng.nextBool()) .one else .zero,
            .basis = if (self.prng.nextBool()) .diagonal else .rectilinear,
        };
    }

    // Bob이 qubit 측정
    pub fn bobMeasure(self: *BB84Channel, qubit: Qubit) struct { state: QubitState, basis: QubitBasis } {
        const bob_basis: QubitBasis = if (self.prng.nextBool()) .diagonal else .rectilinear;
        const measured_state: QubitState = if (bob_basis == qubit.basis)
            qubit.state
        else
            (if (self.prng.nextBool()) .one else .zero);
        return .{ .state = measured_state, .basis = bob_basis };
    }

    // 기저 비교 후 공개 채널로 키 추출
    pub fn siftKey(alice_qubit: Qubit, bob_result: anytype) ?u1 {
        if (alice_qubit.basis == bob_result.basis) {
            return @intFromEnum(bob_result.state);
        }
        return null;
    }
};

// 드론 간 양자 암호화 통신
pub const DroneQuantumLink = struct {
    drone_a: u32,
    drone_b: u32,
    shared_key: [256]u1,
    key_length: usize,

    pub fn init(drone_a: u32, drone_b: u32) DroneQuantumLink {
        return .{
            .drone_a = drone_a,
            .drone_b = drone_b,
            .shared_key = [_]u1{0} ** 256,
            .key_length = 0,
        };
    }

    pub fn generateKey(self: *DroneQuantumLink, allocator: std.mem.Allocator, n_bits: usize) !void {
        var channel = BB84Channel.init(allocator, self.drone_a * 1000 + self.drone_b, 0.05);
        defer channel.deinit();

        var extracted: usize = 0;
        var attempts: usize = 0;
        while (extracted < n_bits and attempts < n_bits * 4) : (attempts += 1) {
            const qubit = channel.alicePrepare();
            const bob_result = channel.bobMeasure(qubit);
            if (BB84Channel.siftKey(qubit, bob_result)) |bit| {
                if (extracted < 256) {
                    self.shared_key[extracted] = bit;
                    extracted += 1;
                }
            }
        }
        self.key_length = extracted;
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const stdout = std.io.getStdOut().writer();
    try stdout.print("SDACS Quantum Communication — Phase 521\n\n", .{});
    try stdout.print("BB84 Protocol 초기화\n", .{});

    var link = DroneQuantumLink.init(1, 2);
    try link.generateKey(allocator, 128);

    try stdout.print("드론 {d} ↔ 드론 {d}: 양자 키 {d}비트 생성 완료\n", .{
        link.drone_a, link.drone_b, link.key_length,
    });

    var prng = QuantumPRNG.init(42);
    var ones: u32 = 0;
    var i: usize = 0;
    while (i < link.key_length) : (i += 1) {
        _ = prng.next();
        if (link.shared_key[i] == 1) ones += 1;
    }
    const zero_ratio: f64 = @as(f64, @floatFromInt(link.key_length - ones)) / @as(f64, @floatFromInt(link.key_length));
    try stdout.print("키 품질: {d:.3} (0.5 근처가 이상적)\n", .{zero_ratio});
    try stdout.print("양자 통신 초기화 완료.\n", .{});
}
