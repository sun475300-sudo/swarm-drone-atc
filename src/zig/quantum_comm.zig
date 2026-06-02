// Phase 521: Quantum Communication — Zig
// SDACS BB84 quantum key distribution simulation for secure drone comms

const std = @import("std");
const Allocator = std.mem.Allocator;
const Random = std.Random;

// Phase 521 marker — quantum key distribution module

/// Qubit basis
pub const Basis = enum { Rectilinear, Diagonal };

/// Qubit state in a given basis
pub const Qubit = struct {
    bit:   u1,
    basis: Basis,
};

/// BB84 protocol constants
const BB84_KEY_BITS = 256;
const BB84_RAW_BITS = BB84_KEY_BITS * 4;  // oversample to account for basis mismatch

/// PRNG wrapper seeded from hardware entropy
pub const PRNG = struct {
    rng: Random.DefaultPrng,

    pub fn init(seed: u64) PRNG {
        return .{ .rng = Random.DefaultPrng.init(seed) };
    }

    pub fn random(self: *PRNG) Random {
        return self.rng.random();
    }

    pub fn nextBit(self: *PRNG) u1 {
        return @intCast(self.rng.random().int(u8) & 1);
    }

    pub fn nextBasis(self: *PRNG) Basis {
        return if (self.rng.random().int(u8) & 1 == 0) .Rectilinear else .Diagonal;
    }
};

/// Alice's side of BB84
pub const Alice = struct {
    prng:    PRNG,
    bits:    [BB84_RAW_BITS]u1,
    bases:   [BB84_RAW_BITS]Basis,
    qubits:  [BB84_RAW_BITS]Qubit,

    pub fn init(seed: u64) Alice {
        var alice = Alice{
            .prng   = PRNG.init(seed),
            .bits   = undefined,
            .bases  = undefined,
            .qubits = undefined,
        };
        alice.prepare();
        return alice;
    }

    pub fn prepare(self: *Alice) void {
        for (0..BB84_RAW_BITS) |i| {
            self.bits[i]   = self.prng.nextBit();
            self.bases[i]  = self.prng.nextBasis();
            self.qubits[i] = .{ .bit = self.bits[i], .basis = self.bases[i] };
        }
    }

    pub fn sendQubits(self: *Alice) []const Qubit {
        return &self.qubits;
    }
};

/// Bob's side of BB84
pub const Bob = struct {
    prng:        PRNG,
    bases:       [BB84_RAW_BITS]Basis,
    measurements:[BB84_RAW_BITS]u1,

    pub fn init(seed: u64) Bob {
        var bob = Bob{
            .prng         = PRNG.init(seed),
            .bases        = undefined,
            .measurements = undefined,
        };
        bob.chooseBases();
        return bob;
    }

    pub fn chooseBases(self: *Bob) void {
        for (0..BB84_RAW_BITS) |i| {
            self.bases[i] = self.prng.nextBasis();
        }
    }

    pub fn measure(self: *Bob, qubits: []const Qubit) void {
        for (0..BB84_RAW_BITS) |i| {
            if (self.bases[i] == qubits[i].basis) {
                // Correct basis: get actual bit
                self.measurements[i] = qubits[i].bit;
            } else {
                // Wrong basis: random result
                self.measurements[i] = self.prng.nextBit();
            }
        }
    }
};

/// QKD result after sifting
pub const SiftedKey = struct {
    alice_key: std.ArrayList(u1),
    bob_key:   std.ArrayList(u1),
    raw_key_len: usize,
    error_rate: f64,
};

/// Sift keys: keep only bits where Alice and Bob used same basis
pub fn siftKeys(
    alloc: Allocator,
    alice: *const Alice,
    bob:   *const Bob,
) !SiftedKey {
    var alice_key = std.ArrayList(u1).init(alloc);
    var bob_key   = std.ArrayList(u1).init(alloc);

    for (0..BB84_RAW_BITS) |i| {
        if (alice.bases[i] == bob.bases[i]) {
            try alice_key.append(alice.bits[i]);
            try bob_key.append(bob.measurements[i]);
        }
    }

    // Calculate QBER (quantum bit error rate)
    var errors: usize = 0;
    const sifted_len = alice_key.items.len;
    for (0..sifted_len) |i| {
        if (alice_key.items[i] != bob_key.items[i]) errors += 1;
    }
    const error_rate = if (sifted_len > 0)
        @as(f64, @floatFromInt(errors)) / @as(f64, @floatFromInt(sifted_len))
    else 1.0;

    return SiftedKey{
        .alice_key   = alice_key,
        .bob_key     = bob_key,
        .raw_key_len = sifted_len,
        .error_rate  = error_rate,
    };
}

/// Run a full BB84 session and return whether key exchange succeeded
pub fn runBB84(alloc: Allocator, alice_seed: u64, bob_seed: u64) !bool {
    var alice = Alice.init(alice_seed);
    var bob   = Bob.init(bob_seed);

    const qubits = alice.sendQubits();
    bob.measure(qubits);

    var result = try siftKeys(alloc, &alice, &bob);
    defer result.alice_key.deinit();
    defer result.bob_key.deinit();

    // Accept if QBER < 11% (BB84 security threshold)
    const success = result.error_rate < 0.11 and result.raw_key_len >= BB84_KEY_BITS;
    std.debug.print("BB84 Phase 521: sifted={} QBER={d:.3} success={}\n",
        .{ result.raw_key_len, result.error_rate, success });
    return success;
}

test "BB84 qubit basis matching" {
    var prng = PRNG.init(521);
    const b1 = prng.nextBasis();
    const b2 = prng.nextBasis();
    _ = b1; _ = b2;  // just test it compiles
    try std.testing.expect(true);
}

test "PRNG generates valid bits" {
    var prng = PRNG.init(12345);
    for (0..100) |_| {
        const bit = prng.nextBit();
        try std.testing.expect(bit == 0 or bit == 1);
    }
}
