// Phase 521 — Quantum Communication Stub: BB84 Protocol Simulation
// Implements a simplified BB84 quantum key distribution protocol stub.

const std = @import("std");

/// Quantum basis choices for BB84
pub const Basis = enum {
    rectilinear, // +: measures 0 or 1
    diagonal,    // x: measures 0 or 1
};

/// A single qubit representation in BB84 simulation
pub const Qubit = struct {
    value: u1,
    basis: Basis,

    pub fn init(value: u1, basis: Basis) Qubit {
        return Qubit{ .value = value, .basis = basis };
    }

    /// Measure the qubit in a given basis; if wrong basis, result is random (PRNG).
    pub fn measure(self: Qubit, measure_basis: Basis, rng: *std.rand.Xoshiro256) u1 {
        if (self.basis == measure_basis) {
            return self.value;
        }
        // Wrong basis — result is random (prng-driven)
        return @intCast(rng.next() % 2);
    }
};

/// BB84 session state shared between Alice and Bob
pub const BB84Session = struct {
    key_bits: std.ArrayList(u1),
    error_rate: f64,
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) BB84Session {
        return BB84Session{
            .key_bits = std.ArrayList(u1).init(allocator),
            .error_rate = 0.0,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *BB84Session) void {
        self.key_bits.deinit();
    }
};

/// Alice generates n qubits with random values and bases using PRNG
pub fn aliceGenerateQubits(n: usize, rng: *std.rand.Xoshiro256, allocator: std.mem.Allocator) ![]Qubit {
    var qubits = try allocator.alloc(Qubit, n);
    for (qubits) |*q| {
        const val: u1 = @intCast(rng.next() % 2);
        const basis: Basis = if (rng.next() % 2 == 0) .rectilinear else .diagonal;
        q.* = Qubit.init(val, basis);
    }
    return qubits;
}

/// Bob measures qubits with randomly chosen bases using PRNG
pub fn bobMeasure(qubits: []const Qubit, rng: *std.rand.Xoshiro256, allocator: std.mem.Allocator) ![]u1 {
    var results = try allocator.alloc(u1, qubits.len);
    var local_rng = rng.*;
    for (qubits, 0..) |q, i| {
        const bob_basis: Basis = if (local_rng.next() % 2 == 0) .rectilinear else .diagonal;
        results[i] = q.measure(bob_basis, &local_rng);
    }
    return results;
}

/// Sift key: keep bits where both Alice and Bob used the same basis.
pub fn siftKey(alice_qubits: []const Qubit, alice_bases: []const Basis, bob_bases: []const Basis, bob_bits: []const u1, session: *BB84Session) !void {
    var errors: usize = 0;
    var total: usize = 0;
    for (alice_qubits, 0..) |q, i| {
        if (alice_bases[i] == bob_bases[i]) {
            try session.key_bits.append(q.value);
            if (q.value != bob_bits[i]) errors += 1;
            total += 1;
        }
    }
    session.error_rate = if (total > 0) @as(f64, @floatFromInt(errors)) / @as(f64, @floatFromInt(total)) else 0.0;
}

/// Check if eavesdropping likely occurred (error rate exceeds threshold)
pub fn detectEavesdropping(session: *const BB84Session, threshold: f64) bool {
    return session.error_rate > threshold;
}

/// Privacy amplification placeholder — hashes the key bits
pub fn privacyAmplify(session: *BB84Session, allocator: std.mem.Allocator) ![]u8 {
    var hasher = std.crypto.hash.sha2.Sha256.init(.{});
    for (session.key_bits.items) |bit| {
        hasher.update(&[_]u8{bit});
    }
    var digest = try allocator.alloc(u8, 32);
    hasher.final(digest[0..32]);
    return digest;
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var rng = std.rand.Xoshiro256.init(0xdeadbeef);
    std.debug.print("BB84 Quantum Key Distribution — Phase 521\n", .{});

    const n = 128;
    const qubits = try aliceGenerateQubits(n, &rng, allocator);
    defer allocator.free(qubits);

    var session = BB84Session.init(allocator);
    defer session.deinit();

    std.debug.print("Generated {} qubits with PRNG\n", .{n});
    std.debug.print("BB84 protocol stub initialized successfully\n", .{});
}
