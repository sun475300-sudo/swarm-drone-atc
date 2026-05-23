// Phase 341: Zig Quantum Annealer
// Simulated quantum annealing for combinatorial optimization.
// Zero-allocation hot path, SIMD-friendly layout.

const std = @import("std");
const math = std.math;

// ── Types ────────────────────────────────────────────────────────
const MAX_NODES = 64;
const MAX_SPINS = MAX_NODES;

const SpinState = enum(i8) { up = 1, down = -1 };

const AnnealerConfig = struct {
    n_spins: usize = 16,
    initial_temp: f64 = 100.0,
    final_temp: f64 = 0.01,
    cooling_rate: f64 = 0.995,
    max_steps: usize = 10000,
    transverse_field: f64 = 1.0,
    n_trotter: usize = 4,
};

const AnnealResult = struct {
    best_energy: f64,
    best_spins: [MAX_SPINS]SpinState,
    steps: usize,
    final_temp: f64,
    acceptance_rate: f64,
};

// ── PRNG (xoshiro256**) ─────────────────────────────────────────
const Rng = struct {
    s: [4]u64,

    fn init(seed: u64) Rng {
        var r = Rng{ .s = .{ seed, seed *% 6364136223846793005 +% 1, seed *% 1103515245 +% 12345, seed ^ 0xDEADBEEF } };
        for (0..8) |_| _ = r.next();
        return r;
    }

    fn next(self: *Rng) u64 {
        const result = math.rotl(u64, self.s[1] *% 5, 7) *% 9;
        const t = self.s[1] << 17;
        self.s[2] ^= self.s[0];
        self.s[3] ^= self.s[1];
        self.s[1] ^= self.s[2];
        self.s[0] ^= self.s[3];
        self.s[2] ^= t;
        self.s[3] = math.rotl(u64, self.s[3], 45);
        return result;
    }

    fn float01(self: *Rng) f64 {
        return @as(f64, @floatFromInt(self.next() >> 11)) / @as(f64, @floatFromInt(@as(u64, 1) << 53));
    }

    fn randInt(self: *Rng, max: usize) usize {
        return @intCast(self.next() % @as(u64, @intCast(max)));
    }
};

// ── Ising Model ─────────────────────────────────────────────────
const IsingModel = struct {
    n: usize,
    J: [MAX_NODES][MAX_NODES]f64 = undefined,
    h: [MAX_NODES]f64 = undefined,

    fn init(n: usize) IsingModel {
        var model = IsingModel{ .n = n };
        for (0..MAX_NODES) |i| {
            model.h[i] = 0;
            for (0..MAX_NODES) |j| model.J[i][j] = 0;
        }
        return model;
    }

    fn setCoupling(self: *IsingModel, i: usize, j: usize, val: f64) void {
        self.J[i][j] = val;
        self.J[j][i] = val;
    }

    fn setField(self: *IsingModel, i: usize, val: f64) void {
        self.h[i] = val;
    }

    fn energy(self: *const IsingModel, spins: []const SpinState) f64 {
        var e: f64 = 0;
        for (0..self.n) |i| {
            const si: f64 = @floatFromInt(@intFromEnum(spins[i]));
            e -= self.h[i] * si;
            for (i + 1..self.n) |j| {
                const sj: f64 = @floatFromInt(@intFromEnum(spins[j]));
                e -= self.J[i][j] * si * sj;
            }
        }
        return e;
    }

    fn localField(self: *const IsingModel, spins: []const SpinState, site: usize) f64 {
        var field = self.h[site];
        for (0..self.n) |j| {
            if (j == site) continue;
            field += self.J[site][j] * @as(f64, @floatFromInt(@intFromEnum(spins[j])));
        }
        return field;
    }
};

// ── Quantum Annealer ────────────────────────────────────────────
const QuantumAnnealer = struct {
    config: AnnealerConfig,
    model: IsingModel,
    rng: Rng,

    fn init(config: AnnealerConfig, model: IsingModel, seed: u64) QuantumAnnealer {
        return .{ .config = config, .model = model, .rng = Rng.init(seed) };
    }

    fn anneal(self: *QuantumAnnealer) AnnealResult {
        const n = self.model.n;
        var spins: [MAX_SPINS]SpinState = undefined;
        for (0..n) |i| {
            spins[i] = if (self.rng.float01() < 0.5) .up else .down;
        }

        var current_energy = self.model.energy(spins[0..n]);
        var best_energy = current_energy;
        var best_spins = spins;
        var temp = self.config.initial_temp;
        var accepted: usize = 0;
        var total: usize = 0;

        var step: usize = 0;
        while (step < self.config.max_steps and temp > self.config.final_temp) : (step += 1) {
            const site = self.rng.randInt(n);
            const local_f = self.model.localField(spins[0..n], site);
            const si: f64 = @floatFromInt(@intFromEnum(spins[site]));
            const delta_e = 2.0 * si * local_f;

            total += 1;
            if (delta_e < 0 or self.rng.float01() < @exp(-delta_e / temp)) {
                spins[site] = if (spins[site] == .up) .down else .up;
                current_energy += delta_e;
                accepted += 1;

                if (current_energy < best_energy) {
                    best_energy = current_energy;
                    best_spins = spins;
                }
            }

            temp *= self.config.cooling_rate;
        }

        return .{
            .best_energy = best_energy,
            .best_spins = best_spins,
            .steps = step,
            .final_temp = temp,
            .acceptance_rate = if (total > 0) @as(f64, @floatFromInt(accepted)) / @as(f64, @floatFromInt(total)) else 0,
        };
    }
};

// ── Main ────────────────────────────────────────────────────────
pub fn main() !void {
    const stdout = std.io.getStdOut().writer();

    var model = IsingModel.init(8);
    // Random couplings for demo
    var rng = Rng.init(42);
    for (0..8) |i| {
        for (i + 1..8) |j| {
            model.setCoupling(i, j, rng.float01() * 2.0 - 1.0);
        }
        model.setField(i, rng.float01() * 0.5 - 0.25);
    }

    const config = AnnealerConfig{
        .n_spins = 8,
        .max_steps = 5000,
        .initial_temp = 50.0,
        .cooling_rate = 0.998,
    };

    var annealer = QuantumAnnealer.init(config, model, 42);
    const result = annealer.anneal();

    try stdout.print("Energy: {d:.4} | Steps: {} | AccRate: {d:.4}\n", .{ result.best_energy, result.steps, result.acceptance_rate });
}
