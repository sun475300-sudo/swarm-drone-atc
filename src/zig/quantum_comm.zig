// Phase 521 — BB84 quantum key distribution protocol for drone-to-drone secure comms.
// Simulates qubit state preparation, photon transmission, basis reconciliation, and PRNG seeding.

const std = @import("std");
const math = std.math;

// --- Constants ---
pub const PHASE_MARKER: u32 = 521;
pub const KEY_LENGTH_BITS: usize = 256;
pub const QUBIT_POOL_SIZE: usize = 1024;
pub const EAVESDROP_THRESHOLD: f64 = 0.11; // QBER threshold for aborting

// --- Qubit basis and state enums ---
pub const Basis = enum { Rectilinear, Diagonal };
pub const QubitState = enum { Zero, One, Plus, Minus };

// --- Single qubit representation ---
pub const Qubit = struct {
    state: QubitState,
    basis: Basis,
    measured_bit: ?u1,

    pub fn init(state: QubitState, basis: Basis) Qubit {
        return .{ .state = state, .basis = basis, .measured_bit = null };
    }
};

// --- PRNG context seeded with drone ID + timestamp for reproducibility ---
// PRNG seeding combines drone identity with wall-clock nonce to ensure
// unique key material per session without requiring hardware entropy.
pub const PrngContext = struct {
    rng: std.rand.DefaultPrng,

    pub fn initWithSeed(drone_id: u64, timestamp_ns: u64) PrngContext {
        const seed: u64 = drone_id ^ (timestamp_ns *% 0x9e3779b97f4a7c15);
        return .{ .rng = std.rand.DefaultPrng.init(seed) };
    }

    pub fn randomBasis(self: *PrngContext) Basis {
        return if (self.rng.random().boolean()) .Rectilinear else .Diagonal;
    }

    pub fn randomBit(self: *PrngContext) u1 {
        return @intCast(self.rng.random().int(u1));
    }
};

// --- BB84 sender: prepares qubits according to random basis and bit value ---
pub fn bb84PrepareBatch(
    prng: *PrngContext,
    out_qubits: []Qubit,
    out_bits: []u1,
    out_bases: []Basis,
) void {
    std.debug.assert(out_qubits.len == out_bits.len);
    std.debug.assert(out_qubits.len == out_bases.len);
    for (out_qubits, 0..) |*q, i| {
        const bit = prng.randomBit();
        const basis = prng.randomBasis();
        out_bits[i] = bit;
        out_bases[i] = basis;
        // Map (basis, bit) -> QubitState: BB84 encoding table
        q.* = Qubit.init(switch (basis) {
            .Rectilinear => if (bit == 0) .Zero else .One,
            .Diagonal => if (bit == 0) .Plus else .Minus,
        }, basis);
    }
}

// --- BB84 receiver: measures each qubit with a randomly chosen basis ---
// If bases match, result is deterministic (no collapse); otherwise random
// (simulates quantum measurement collapse / photon projection).
pub fn bb84MeasureBatch(
    prng: *PrngContext,
    qubits: []const Qubit,
    out_meas_bases: []Basis,
    out_meas_bits: []u1,
) void {
    std.debug.assert(qubits.len == out_meas_bases.len);
    std.debug.assert(qubits.len == out_meas_bits.len);
    for (qubits, 0..) |q, i| {
        const meas_basis = prng.randomBasis();
        out_meas_bases[i] = meas_basis;
        if (meas_basis == q.basis) {
            out_meas_bits[i] = switch (q.state) {
                .Zero, .Plus => 0,
                .One, .Minus => 1,
            };
        } else {
            // Incompatible basis: photon measurement collapses to random bit
            out_meas_bits[i] = prng.randomBit();
        }
    }
}

// --- Basis reconciliation: sift to matching-basis positions only ---
pub fn siftKey(
    send_bases: []const Basis,
    meas_bases: []const Basis,
    send_bits: []const u1,
    meas_bits: []const u1,
    out_alice: []u1,
    out_bob: []u1,
) usize {
    var count: usize = 0;
    for (send_bases, 0..) |sb, i| {
        if (sb == meas_bases[i]) {
            out_alice[count] = send_bits[i];
            out_bob[count] = meas_bits[i];
            count += 1;
        }
    }
    return count;
}

// --- Compute Quantum Bit Error Rate (QBER) on a sample subset ---
pub fn computeQBER(alice: []const u1, bob: []const u1, sample_size: usize) f64 {
    const n = @min(sample_size, alice.len);
    if (n == 0) return 0.0;
    var errors: usize = 0;
    for (0..n) |i| {
        if (alice[i] != bob[i]) errors += 1;
    }
    return @as(f64, @floatFromInt(errors)) / @as(f64, @floatFromInt(n));
}

// --- Pack sifted bits into byte slice (256-bit shared secret) ---
fn packBits(bits: []const u1, out: []u8, count: usize) void {
    const usable = @min(count, out.len * 8);
    for (0..usable) |i| {
        const byte_idx = i / 8;
        const bit_idx: u3 = @intCast(i % 8);
        out[byte_idx] |= @as(u8, bits[i]) << bit_idx;
    }
}

// --- High-level BB84 key exchange entry point ---
pub fn bb84KeyExchange(
    alice_drone_id: u64,
    bob_drone_id: u64,
    timestamp_ns: u64,
    allocator: std.mem.Allocator,
) ![]u8 {
    var alice_prng = PrngContext.initWithSeed(alice_drone_id, timestamp_ns);
    var bob_prng = PrngContext.initWithSeed(bob_drone_id, timestamp_ns ^ 0xdeadbeef);

    const pool = QUBIT_POOL_SIZE;
    const qubits = try allocator.alloc(Qubit, pool);
    defer allocator.free(qubits);
    const alice_bits = try allocator.alloc(u1, pool);
    defer allocator.free(alice_bits);
    const alice_bases = try allocator.alloc(Basis, pool);
    defer allocator.free(alice_bases);
    const bob_meas_bases = try allocator.alloc(Basis, pool);
    defer allocator.free(bob_meas_bases);
    const bob_meas_bits = try allocator.alloc(u1, pool);
    defer allocator.free(bob_meas_bits);

    bb84PrepareBatch(&alice_prng, qubits, alice_bits, alice_bases);
    bb84MeasureBatch(&bob_prng, qubits, bob_meas_bases, bob_meas_bits);

    const sifted_alice = try allocator.alloc(u1, pool);
    defer allocator.free(sifted_alice);
    const sifted_bob = try allocator.alloc(u1, pool);
    defer allocator.free(sifted_bob);

    const sifted_len = siftKey(alice_bases, bob_meas_bases, alice_bits, bob_meas_bits, sifted_alice, sifted_bob);

    const qber = computeQBER(sifted_alice[0..sifted_len], sifted_bob[0..sifted_len], 50);
    if (qber > EAVESDROP_THRESHOLD) {
        return error.EavesdropDetected;
    }

    const key_bytes = KEY_LENGTH_BITS / 8;
    const key = try allocator.alloc(u8, key_bytes);
    for (key) |*byte| byte.* = 0;
    packBits(sifted_alice[0..sifted_len], key, @min(sifted_len, KEY_LENGTH_BITS));
    return key;
}

// --- Test harness ---
test "BB84 phase marker is 521" {
    try std.testing.expectEqual(@as(u32, 521), PHASE_MARKER);
}

test "PRNG seeding produces deterministic first byte" {
    var p1 = PrngContext.initWithSeed(42, 1_000_000);
    var p2 = PrngContext.initWithSeed(42, 1_000_000);
    try std.testing.expectEqual(p1.randomBit(), p2.randomBit());
}

test "siftKey retains only matching bases" {
    const sb = [_]Basis{ .Rectilinear, .Diagonal, .Rectilinear };
    const mb = [_]Basis{ .Rectilinear, .Rectilinear, .Rectilinear };
    const ab = [_]u1{ 1, 0, 1 };
    const bb = [_]u1{ 1, 1, 1 };
    var oa: [3]u1 = undefined;
    var ob: [3]u1 = undefined;
    const n = siftKey(&sb, &mb, &ab, &bb, &oa, &ob);
    try std.testing.expectEqual(@as(usize, 2), n);
}
