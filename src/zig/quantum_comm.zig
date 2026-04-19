// Phase 521: Zig Quantum Communication — BB84 QKD Protocol
const std = @import("std");

const QKDBasis = enum { Rectilinear, Diagonal };
const QubitState = enum { Zero, One, Plus, Minus };

const QKDResult = struct {
    raw_key_length: u32,
    sifted_key_length: u32,
    error_rate: f64,
    secure: bool,
    key_hash: u64,
};

const PRNG = struct {
    state: u64,

    fn init(seed: u64) PRNG {
        return .{ .state = seed ^ 0x6c62272e07bb0142 };
    }

    fn next(self: *PRNG) u64 {
        self.state ^= self.state << 13;
        self.state ^= self.state >> 7;
        self.state ^= self.state << 17;
        return self.state;
    }

    fn float01(self: *PRNG) f64 {
        return @as(f64, @floatFromInt(self.next() & 0x7FFFFFFF)) / @as(f64, 0x7FFFFFFF);
    }

    fn boolean(self: *PRNG) bool {
        return (self.next() & 1) == 1;
    }

    fn basis(self: *PRNG) QKDBasis {
        return if (self.boolean()) .Rectilinear else .Diagonal;
    }
};

fn prepareQubit(bit: bool, b: QKDBasis) QubitState {
    return switch (b) {
        .Rectilinear => if (bit) .One else .Zero,
        .Diagonal => if (bit) .Minus else .Plus,
    };
}

fn measureQubit(state: QubitState, b: QKDBasis, rng: *PRNG) u1 {
    const state_basis: QKDBasis = switch (state) {
        .Zero, .One => .Rectilinear,
        .Plus, .Minus => .Diagonal,
    };
    if (b == state_basis) {
        return switch (state) {
            .Zero, .Plus => 0,
            .One, .Minus => 1,
        };
    }
    return if (rng.boolean()) @as(u1, 1) else @as(u1, 0);
}

pub fn bb84Execute(n_bits: u32, eve_present: bool, seed: u64) QKDResult {
    var rng = PRNG.init(seed);
    var sifted_matches: u32 = 0;
    var sifted_errors: u32 = 0;
    var key_hash: u64 = 0xcbf29ce484222325;

    var i: u32 = 0;
    while (i < n_bits) : (i += 1) {
        const alice_bit = rng.boolean();
        const alice_basis = rng.basis();
        const bob_basis = rng.basis();

        var qubit = prepareQubit(alice_bit, alice_basis);

        if (eve_present) {
            const eve_basis = rng.basis();
            _ = measureQubit(qubit, eve_basis, &rng);
            qubit = prepareQubit(rng.boolean(), eve_basis);
        }

        const bob_result = measureQubit(qubit, bob_basis, &rng);

        if (alice_basis == bob_basis) {
            sifted_matches += 1;
            const alice_u1: u1 = if (alice_bit) 1 else 0;
            if (alice_u1 != bob_result) {
                sifted_errors += 1;
            }
            key_hash ^= @as(u64, bob_result);
            key_hash *%= 0x100000001b3;
        }
    }

    const error_rate = if (sifted_matches > 0)
        @as(f64, @floatFromInt(sifted_errors)) / @as(f64, @floatFromInt(sifted_matches))
    else
        1.0;

    return .{
        .raw_key_length = n_bits,
        .sifted_key_length = sifted_matches,
        .error_rate = error_rate,
        .secure = error_rate < 0.11,
        .key_hash = key_hash,
    };
}

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    const result = bb84Execute(1024, false, 42);
    try stdout.print("BB84 QKD: raw={d} sifted={d} err={d:.4} secure={}\n", .{
        result.raw_key_length, result.sifted_key_length,
        result.error_rate,     result.secure,
    });
    const eve_result = bb84Execute(1024, true, 42);
    try stdout.print("With Eve: err={d:.4} secure={}\n", .{
        eve_result.error_rate, eve_result.secure,
    });
}
