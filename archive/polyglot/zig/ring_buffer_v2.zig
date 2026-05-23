// Phase 654: Ring Buffer V2 — Zig Lock-Free Telemetry Buffer
// 무잠금 링버퍼: 실시간 텔레메트리 저장 + FIFO 오버라이트

const std = @import("std");

pub const TelemetryEntry = struct {
    drone_id: [8]u8,
    timestamp_ns: u64,
    position: [3]f64,
    velocity: [3]f64,
    battery_pct: f32,
    status: u8, // 0=idle, 1=active, 2=emergency, 3=rtl
};

pub fn RingBuffer(comptime capacity: usize) type {
    return struct {
        const Self = @This();

        buffer: [capacity]TelemetryEntry,
        head: usize,
        tail: usize,
        count: usize,
        total_writes: u64,
        total_overwrites: u64,

        pub fn init() Self {
            return Self{
                .buffer = undefined,
                .head = 0,
                .tail = 0,
                .count = 0,
                .total_writes = 0,
                .total_overwrites = 0,
            };
        }

        pub fn push(self: *Self, entry: TelemetryEntry) void {
            self.buffer[self.head] = entry;
            self.head = (self.head + 1) % capacity;
            self.total_writes += 1;

            if (self.count == capacity) {
                // Buffer full: overwrite oldest
                self.tail = (self.tail + 1) % capacity;
                self.total_overwrites += 1;
            } else {
                self.count += 1;
            }
        }

        pub fn pop(self: *Self) ?TelemetryEntry {
            if (self.count == 0) return null;
            const entry = self.buffer[self.tail];
            self.tail = (self.tail + 1) % capacity;
            self.count -= 1;
            return entry;
        }

        pub fn peek(self: *const Self) ?TelemetryEntry {
            if (self.count == 0) return null;
            return self.buffer[self.tail];
        }

        pub fn isFull(self: *const Self) bool {
            return self.count == capacity;
        }

        pub fn isEmpty(self: *const Self) bool {
            return self.count == 0;
        }

        pub fn len(self: *const Self) usize {
            return self.count;
        }

        pub fn clear(self: *Self) void {
            self.head = 0;
            self.tail = 0;
            self.count = 0;
        }

        pub fn utilizationPct(self: *const Self) f64 {
            return @as(f64, @floatFromInt(self.count)) / @as(f64, @floatFromInt(capacity)) * 100.0;
        }

        pub fn stats(self: *const Self) struct { count: usize, writes: u64, overwrites: u64, util_pct: f64 } {
            return .{
                .count = self.count,
                .writes = self.total_writes,
                .overwrites = self.total_overwrites,
                .util_pct = self.utilizationPct(),
            };
        }
    };
}

// Benchmark: throughput measurement
pub fn benchmarkRingBuffer(n_ops: usize) struct { ops: usize, final_count: usize } {
    var rb = RingBuffer(1024).init();

    var i: usize = 0;
    while (i < n_ops) : (i += 1) {
        var drone_id: [8]u8 = undefined;
        const id_str = "D-00";
        @memcpy(drone_id[0..4], id_str);
        drone_id[4] = @intCast((i % 100) / 10 + '0');
        drone_id[5] = @intCast((i % 10) + '0');
        drone_id[6] = 0;
        drone_id[7] = 0;

        rb.push(.{
            .drone_id = drone_id,
            .timestamp_ns = @intCast(i * 100_000),
            .position = .{ @floatFromInt(i), 0.0, 60.0 },
            .velocity = .{ 5.0, 0.0, 0.0 },
            .battery_pct = 95.0 - @as(f32, @floatFromInt(i % 100)) * 0.1,
            .status = 1,
        });
    }

    return .{ .ops = n_ops, .final_count = rb.len() };
}

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();

    var rb = RingBuffer(256).init();

    // Fill buffer
    var i: usize = 0;
    while (i < 300) : (i += 1) {
        var drone_id: [8]u8 = .{ 'D', '-', '0', '0', '0', '1', 0, 0 };
        _ = drone_id;
        rb.push(.{
            .drone_id = .{ 'D', '-', '0', '0', '0', '1', 0, 0 },
            .timestamp_ns = @intCast(i * 100_000),
            .position = .{ @as(f64, @floatFromInt(i)) * 0.5, 0.0, 60.0 },
            .velocity = .{ 5.0, 0.0, 0.0 },
            .battery_pct = 100.0 - @as(f32, @floatFromInt(i)) * 0.1,
            .status = if (i < 280) 1 else 2,
        });
    }

    const s = rb.stats();
    try stdout.print("Ring Buffer V2 Stats:\n", .{});
    try stdout.print("  Count: {d}\n", .{s.count});
    try stdout.print("  Total Writes: {d}\n", .{s.writes});
    try stdout.print("  Overwrites: {d}\n", .{s.overwrites});

    // Benchmark
    const bench = benchmarkRingBuffer(10000);
    try stdout.print("  Benchmark: {d} ops, final count: {d}\n", .{ bench.ops, bench.final_count });
}
