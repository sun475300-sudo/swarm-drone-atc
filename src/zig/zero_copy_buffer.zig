// Zero-Copy Buffer — Zig for SDACS telemetry I/O pipeline
// Phase 594

const std = @import("std");
const Allocator = std.mem.Allocator;
const assert = std.debug.assert;

/// Lock-free single-producer single-consumer RingBuffer.
/// 'T' is the element type; 'capacity' must be a power of 2.
pub fn RingBuffer(comptime T: type, comptime capacity: usize) type {
    comptime {
        assert(capacity > 0 and std.math.isPowerOfTwo(capacity));
    }
    const mask = capacity - 1;

    return struct {
        const Self = @This();

        buf:  [capacity]T = undefined,
        head: usize = 0,  /// consumer reads from head
        tail: usize = 0,  /// producer writes to tail

        pub fn push(self: *Self, value: T) error{Full}!void {
            const next_tail = (self.tail + 1) & mask;
            if (next_tail == self.head) return error.Full;
            self.buf[self.tail] = value;
            self.tail = next_tail;
        }

        pub fn pop(self: *Self) ?T {
            if (self.head == self.tail) return null;
            const value = self.buf[self.head];
            self.head = (self.head + 1) & mask;
            return value;
        }

        pub fn isEmpty(self: *const Self) bool {
            return self.head == self.tail;
        }

        pub fn isFull(self: *const Self) bool {
            return ((self.tail + 1) & mask) == self.head;
        }

        pub fn len(self: *const Self) usize {
            return (self.tail -% self.head) & mask;
        }

        pub fn capacity(self: *const Self) usize {
            _ = self;
            return capacity;
        }
    };
}

/// Zero-copy telemetry frame (fits in a cache line ~64 bytes)
pub const TelemetryFrame = extern struct {
    drone_id  : u32,
    timestamp : i64,
    lat_e7    : i32,   /// latitude * 1e7 (integer for zero-copy)
    lon_e7    : i32,   /// longitude * 1e7
    alt_mm    : i32,   /// altitude in mm
    speed_cms : u16,   /// speed in cm/s
    heading   : u16,   /// heading 0–35999 (1/100 degree)
    batt_pct  : u8,
    status    : u8,
    crc16     : u16,
};

/// Statically-allocated telemetry ring buffer (1024 slots)
pub const TelemetryRingBuffer = RingBuffer(TelemetryFrame, 1024);

/// Slice-based zero-copy reader for packed binary streams
pub const ZeroCopyReader = struct {
    data   : []const u8,
    cursor : usize = 0,

    pub fn init(data: []const u8) ZeroCopyReader {
        return .{ .data = data, .cursor = 0 };
    }

    pub fn readFrame(self: *ZeroCopyReader) ?*const TelemetryFrame {
        if (self.cursor + @sizeOf(TelemetryFrame) > self.data.len) return null;
        const frame: *const TelemetryFrame = @ptrCast(@alignCast(self.data[self.cursor..].ptr));
        self.cursor += @sizeOf(TelemetryFrame);
        return frame;
    }

    pub fn remaining(self: *const ZeroCopyReader) usize {
        return self.data.len - self.cursor;
    }
};

test "RingBuffer push/pop" {
    var rb = RingBuffer(u32, 8){};
    try std.testing.expect(rb.isEmpty());
    try rb.push(42);
    try rb.push(43);
    try std.testing.expectEqual(@as(?u32, 42), rb.pop());
    try std.testing.expectEqual(@as(?u32, 43), rb.pop());
    try std.testing.expect(rb.isEmpty());
}
