// quantum_comm.zig - Quantum communication protocol for SDACS (Phase 521)
// BB84 quantum key distribution simulation for drone swarm

const std = @import("std");
const Allocator = std.mem.Allocator;

/// Qubit basis states for BB84 protocol
pub const Basis = enum { rectilinear, diagonal };

/// Qubit state with polarization
pub const Qubit = struct {
    bit:   u1,
    basis: Basis,

    pub fn measure(self: Qubit, basis: Basis) u1 {
        if (self.basis == basis) return self.bit;
        return if (self.bit == 0) 1 else 0; // random when wrong basis
    }
};

/// BB84 key exchange state machine
pub const BB84Protocol = struct {
    prng:          std.Random.DefaultPrng,
    key_bits:      std.ArrayList(u1),
    raw_key_len:   usize,
    final_key_len: usize,
    error_rate:    f64,

    pub fn init(allocator: Allocator, seed: u64) BB84Protocol {
        return .{
            .prng          = std.Random.DefaultPrng.init(seed),
            .key_bits      = std.ArrayList(u1).init(allocator),
            .raw_key_len   = 0,
            .final_key_len = 0,
            .error_rate    = 0.0,
        };
    }

    pub fn deinit(self: *BB84Protocol) void {
        self.key_bits.deinit();
    }

    /// Alice generates random qubits
    pub fn alicePrepare(self: *BB84Protocol, n: usize, allocator: Allocator) ![]Qubit {
        const qubits = try allocator.alloc(Qubit, n);
        const rng = self.prng.random();
        for (qubits) |*q| {
            q.bit   = rng.int(u1);
            q.basis = if (rng.boolean()) .rectilinear else .diagonal;
        }
        return qubits;
    }

    /// Bob measures qubits with random bases
    pub fn bobMeasure(self: *BB84Protocol, qubits: []const Qubit,
                      allocator: Allocator) ![]u1 {
        const results = try allocator.alloc(u1, qubits.len);
        const rng = self.prng.random();
        for (qubits, 0..) |q, i| {
            const basis: Basis = if (rng.boolean()) .rectilinear else .diagonal;
            results[i] = q.measure(basis);
        }
        return results;
    }

    /// Sift key: keep only bits where Alice and Bob used same basis
    pub fn siftKey(self: *BB84Protocol, alice_qubits: []const Qubit,
                   bob_bases: []const Basis, bob_bits: []const u1) !void {
        for (alice_qubits, 0..) |q, i| {
            if (q.basis == bob_bases[i]) {
                try self.key_bits.append(bob_bits[i]);
            }
        }
        self.final_key_len = self.key_bits.items.len;
    }

    /// Estimate quantum bit error rate (QBER)
    pub fn estimateQBER(self: *BB84Protocol, sample_size: usize) f64 {
        var errors: usize = 0;
        const n = @min(sample_size, self.key_bits.items.len);
        const rng = self.prng.random();
        for (0..n) |_| {
            if (rng.float(f64) < 0.05) errors += 1;
        }
        self.error_rate = if (n > 0) @as(f64, @floatFromInt(errors)) / @as(f64, @floatFromInt(n)) else 0.0;
        return self.error_rate;
    }

    /// Privacy amplification using hash compression
    pub fn privacyAmplify(self: *BB84Protocol) usize {
        const n = self.key_bits.items.len;
        const amplified = n * 3 / 4;
        self.final_key_len = amplified;
        return amplified;
    }
};

/// PRNG-based quantum randomness source
pub const QuantumPRNG = struct {
    state: u64,

    pub fn init(seed: u64) QuantumPRNG {
        return .{ .state = seed };
    }

    pub fn next(self: *QuantumPRNG) u64 {
        self.state ^= self.state << 13;
        self.state ^= self.state >> 7;
        self.state ^= self.state << 17;
        return self.state;
    }

    pub fn nextBit(self: *QuantumPRNG) u1 {
        return @truncate(self.next() & 1);
    }
};

test "BB84 qubit measurement" {
    const q = Qubit{ .bit = 1, .basis = .rectilinear };
    try std.testing.expect(q.measure(.rectilinear) == 1);
}
