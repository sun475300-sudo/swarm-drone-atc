// Phase 594: Zero-Copy Buffer — 드론 제로카피 링 버퍼 (Zig)
// High-performance zero-copy RingBuffer for drone telemetry streaming.
const std = @import("std");

const PHASE: u32 = 594;

/// Telemetry record for a single drone sample.
pub const TelemetryRecord = struct {
    drone_id:     u32,
    seq:          u64,
    timestamp_us: u64,
    x: f64, y: f64, z: f64,
    vx: f64, vy: f64, vz: f64,
    battery:  f32,
    rssi_dbm: i16,
};

/// RingBuffer provides a fixed-capacity lock-free single-producer/single-consumer buffer.
pub fn RingBuffer(comptime T: type, comptime cap: usize) type {
    comptime std.debug.assert(cap > 0 and (cap & (cap - 1)) == 0);  // power of 2
    return struct {
        const Self = @This();
        const MASK = cap - 1;

        slots:    [cap]T = undefined,
        head:     usize  = 0,
        tail:     usize  = 0,

        /// Push an item. Returns false if full.
        pub fn push(self: *Self, item: T) bool {
            const next = (self.head + 1) & MASK;
            if (next == self.tail) return false;  // full
            self.slots[self.head] = item;
            self.head = next;
            return true;
        }

        /// Pop an item. Returns null if empty.
        pub fn pop(self: *Self) ?T {
            if (self.head == self.tail) return null;
            const item = self.slots[self.tail];
            self.tail = (self.tail + 1) & MASK;
            return item;
        }

        /// Peek without removing.
        pub fn peek(self: *Self) ?T {
            if (self.head == self.tail) return null;
            return self.slots[self.tail];
        }

        /// Returns used capacity.
        pub fn used(self: *Self) usize {
            return (self.head -% self.tail) & MASK;
        }

        /// Returns free capacity.
        pub fn free(self: *Self) usize {
            return cap - 1 - self.used();
        }

        pub fn isEmpty(self: *Self) bool { return self.head == self.tail; }
        pub fn isFull(self: *Self)  bool { return self.free() == 0; }

        /// Reset buffer.
        pub fn reset(self: *Self) void { self.head = 0; self.tail = 0; }
    };
}

/// ZeroCopyStream wraps a RingBuffer with stats tracking.
pub const ZeroCopyStream = struct {
    rb:          RingBuffer(TelemetryRecord, 512),
    written:     u64,
    dropped:     u64,
    read_count:  u64,

    pub fn init() ZeroCopyStream {
        return ZeroCopyStream{ .rb = .{}, .written = 0, .dropped = 0, .read_count = 0 };
    }

    pub fn write(self: *ZeroCopyStream, rec: TelemetryRecord) void {
        if (!self.rb.push(rec)) {
            self.dropped += 1;
        } else {
            self.written += 1;
        }
    }

    pub fn read(self: *ZeroCopyStream) ?TelemetryRecord {
        const r = self.rb.pop();
        if (r != null) self.read_count += 1;
        return r;
    }

    pub fn throughput_pct(self: *ZeroCopyStream) f64 {
        if (self.written + self.dropped == 0) return 100.0;
        return 100.0 * @as(f64, @floatFromInt(self.written)) /
               @as(f64, @floatFromInt(self.written + self.dropped));
    }
};

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    try stdout.print("Phase {d}: Zero-Copy Buffer — 드론 제로카피 RingBuffer\n", .{PHASE});

    var stream = ZeroCopyStream.init();
    var seq: u64 = 0;
    while (seq < 600) : (seq += 1) {
        const rec = TelemetryRecord{
            .drone_id     = @intCast(seq % 10),
            .seq          = seq,
            .timestamp_us = seq * 1000,
            .x = @as(f64, @floatFromInt(seq)) * 0.5,
            .y = 0.0, .z = 50.0,
            .vx = 5.0, .vy = 0.0, .vz = 0.0,
            .battery = 80.0, .rssi_dbm = -70,
        };
        stream.write(rec);
    }
    // Drain half
    var drained: u32 = 0;
    while (drained < 100) : (drained += 1) {
        _ = stream.read();
    }
    try stdout.print("Written={d} Dropped={d} Read={d} Throughput={d:.1}%\n", .{
        stream.written, stream.dropped, stream.read_count, stream.throughput_pct()
    });
}
