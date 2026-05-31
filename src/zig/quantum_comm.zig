// P521: QuantumComm - Zig BB84 quantum key distribution simulation
// Phase 521: Quantum-safe communication for drone swarms using BB84 protocol

const std = @import("std");

// BB84 qubit basis types
const Basis = enum { rectilinear, diagonal };
const BitValue = enum(u1) { zero = 0, one = 1 };

// Qubit state
const Qubit = struct {
    basis: Basis,
    value: BitValue,
};

// BB84 key distribution
const BB84 = struct {
    prng: std.rand.DefaultPrng,
    key_bits: std.ArrayList(u1),

    pub fn init(seed: u64, allocator: std.mem.Allocator) BB84 {
        return BB84{
            .prng = std.rand.DefaultPrng.init(seed),
            .key_bits = std.ArrayList(u1).init(allocator),
        };
    }

    pub fn deinit(self: *BB84) void {
        self.key_bits.deinit();
    }

    // Alice prepares qubits
    pub fn prepare_qubits(self: *BB84, n: usize, allocator: std.mem.Allocator) ![]Qubit {
        var qubits = try allocator.alloc(Qubit, n);
        const rng = self.prng.random();
        for (qubits) |*q| {
            q.basis = if (rng.boolean()) .rectilinear else .diagonal;
            q.value = if (rng.boolean()) .one else .zero;
        }
        return qubits;
    }

    // Bob measures qubits with random bases
    pub fn measure_qubits(self: *BB84, qubits: []const Qubit, allocator: std.mem.Allocator) ![]Qubit {
        var measured = try allocator.alloc(Qubit, qubits.len);
        const rng = self.prng.random();
        for (qubits, 0..) |q, i| {
            const bob_basis: Basis = if (rng.boolean()) .rectilinear else .diagonal;
            measured[i] = Qubit{
                .basis = bob_basis,
                .value = if (bob_basis == q.basis) q.value
                         else if (rng.boolean()) .one else .zero,
            };
        }
        return measured;
    }

    // Sift key: keep bits where bases matched
    pub fn sift_key(self: *BB84, alice: []const Qubit, bob: []const Qubit) !void {
        self.key_bits.clearRetainingCapacity();
        for (alice, bob) |a, b| {
            if (a.basis == b.basis) {
                try self.key_bits.append(@intFromEnum(a.value));
            }
        }
    }

    pub fn key_length(self: *const BB84) usize {
        return self.key_bits.items.len;
    }
};

// PRNG-based secure random for key generation (fallback when quantum hardware unavailable)
const SecureRandom = struct {
    prng: std.rand.DefaultPrng,

    pub fn init(seed: u64) SecureRandom {
        return SecureRandom{ .prng = std.rand.DefaultPrng.init(seed) };
    }

    pub fn next_u32(self: *SecureRandom) u32 {
        return self.prng.random().int(u32);
    }

    pub fn next_key(self: *SecureRandom, len: usize, buf: []u8) void {
        for (buf[0..len]) |*b| {
            b.* = self.prng.random().int(u8);
        }
    }
};
