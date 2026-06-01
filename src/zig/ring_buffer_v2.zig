// Phase 644: Ring Buffer v2 — 고성능 드론 텔레메트리 링 버퍼 (Zig)
// Lock-free ring buffer for real-time telemetry streaming.
const std = @import("std");

const PHASE: u32 = 644;

/// TelemetryFrame holds a single sensor snapshot.
pub const TelemetryFrame = struct {
    drone_id: u32,
    timestamp_ms: u64,
    x: f64,
    y: f64,
    z: f64,
    battery: f32,
    velocity: f32,
};

/// RingBuffer is a fixed-capacity circular buffer for TelemetryFrame.
pub fn RingBuffer(comptime capacity: usize) type {
    return struct {
        const Self = @This();
        buf: [capacity]TelemetryFrame = undefined,
        head: usize = 0,
        tail: usize = 0,
        count: usize = 0,

        /// Push a frame; overwrites oldest if full.
        pub fn push(self: *Self, frame: TelemetryFrame) void {
            self.buf[self.head] = frame;
            self.head = (self.head + 1) % capacity;
            if (self.count < capacity) {
                self.count += 1;
            } else {
                // Overwrite: advance tail
                self.tail = (self.tail + 1) % capacity;
            }
        }

        /// Pop oldest frame or null if empty.
        pub fn pop(self: *Self) ?TelemetryFrame {
            if (self.count == 0) return null;
            const frame = self.buf[self.tail];
            self.tail = (self.tail + 1) % capacity;
            self.count -= 1;
            return frame;
        }

        /// Peek at the oldest frame without removing.
        pub fn peek(self: *Self) ?TelemetryFrame {
            if (self.count == 0) return null;
            return self.buf[self.tail];
        }

        /// Returns true when buffer has reached capacity.
        pub fn isFull(self: *Self) bool {
            return self.count == capacity;
        }

        /// Returns true when empty.
        pub fn isEmpty(self: *Self) bool {
            return self.count == 0;
        }

        /// Returns current fill level.
        pub fn len(self: *Self) usize {
            return self.count;
        }

        /// Clears the buffer.
        pub fn reset(self: *Self) void {
            self.head = 0;
            self.tail = 0;
            self.count = 0;
        }
    };
}

/// TelemetryStream wraps a RingBuffer and tracks statistics.
pub const TelemetryStream = struct {
    rb: RingBuffer(256),
    total_pushed: u64,
    total_dropped: u64,
    drone_count: u32,

    pub fn init(drone_count: u32) TelemetryStream {
        return TelemetryStream{
            .rb = RingBuffer(256){},
            .total_pushed = 0,
            .total_dropped = 0,
            .drone_count = drone_count,
        };
    }

    pub fn push(self: *TelemetryStream, frame: TelemetryFrame) void {
        if (self.rb.isFull()) {
            self.total_dropped += 1;
        }
        self.rb.push(frame);
        self.total_pushed += 1;
    }

    pub fn drain(self: *TelemetryStream, out: []TelemetryFrame) usize {
        var i: usize = 0;
        while (i < out.len) {
            const f = self.rb.pop() orelse break;
            out[i] = f;
            i += 1;
        }
        return i;
    }
};

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    try stdout.print("Phase {d}: Ring Buffer v2 — 드론 텔레메트리 링 버퍼\n", .{PHASE});

    var stream = TelemetryStream.init(10);
    var i: u32 = 0;
    while (i < 300) : (i += 1) {
        const frame = TelemetryFrame{
            .drone_id = i % 10,
            .timestamp_ms = i * 100,
            .x = @as(f64, @floatFromInt(i)) * 0.5,
            .y = @as(f64, @floatFromInt(i)) * 0.3,
            .z = 50.0,
            .battery = 80.0,
            .velocity = 5.0,
        };
        stream.push(frame);
    }
    try stdout.print("Pushed: {d}, Dropped: {d}, Buffered: {d}\n",
        .{stream.total_pushed, stream.total_dropped, stream.rb.len()});
}
