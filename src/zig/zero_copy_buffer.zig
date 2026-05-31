// P594: ZeroCopyBuffer - Zig lock-free ring buffer for zero-copy telemetry
// Phase 594: High-performance ring buffer with atomic operations

const std = @import("std");
const assert = std.debug.assert;
const Atomic = std.atomic.Value;

/// Generic ring buffer with power-of-2 capacity for efficient masking
pub fn RingBuffer(comptime T: type, comptime capacity: usize) type {
    comptime assert(std.math.isPowerOfTwo(capacity));

    return struct {
        const Self = @This();
        const MASK = capacity - 1;

        data:     [capacity]T = undefined,
        head:     Atomic(usize) = Atomic(usize).init(0),
        tail:     Atomic(usize) = Atomic(usize).init(0),

        /// Push item. Returns true on success, false if full.
        pub fn push(self: *Self, item: T) bool {
            const t = self.tail.load(.monotonic);
            const next_t = (t + 1) & MASK;
            const h = self.head.load(.acquire);
            if (next_t == h) return false;  // full
            self.data[t] = item;
            self.tail.store(next_t, .release);
            return true;
        }

        /// Pop item. Returns null if empty.
        pub fn pop(self: *Self) ?T {
            const h = self.head.load(.monotonic);
            const t = self.tail.load(.acquire);
            if (h == t) return null;  // empty
            const item = self.data[h];
            self.head.store((h + 1) & MASK, .release);
            return item;
        }

        /// Peek at head without consuming. Returns null if empty.
        pub fn peek(self: *const Self) ?T {
            const h = self.head.load(.monotonic);
            const t = self.tail.load(.acquire);
            if (h == t) return null;
            return self.data[h];
        }

        pub fn len(self: *const Self) usize {
            const h = self.head.load(.monotonic);
            const t = self.tail.load(.monotonic);
            return (t -% h) & MASK;
        }

        pub fn isEmpty(self: *const Self) bool {
            return self.head.load(.monotonic) == self.tail.load(.monotonic);
        }

        pub fn isFull(self: *const Self) bool {
            const h = self.head.load(.monotonic);
            const t = self.tail.load(.monotonic);
            return ((t + 1) & MASK) == h;
        }
    };
}

/// Drone telemetry frame for zero-copy streaming
pub const TelemetryFrame = struct {
    drone_id:     u32,
    timestamp_us: u64,
    x: f32, y: f32, z: f32,
    vx: f32, vy: f32, vz: f32,
    battery: f32,
    status: u8,
    checksum: u16,

    pub fn computeChecksum(self: *const TelemetryFrame) u16 {
        var csum: u32 = self.drone_id;
        csum +%= @as(u32, @intFromFloat(self.x * 100.0));
        csum +%= @as(u32, @intFromFloat(self.y * 100.0));
        csum +%= @as(u32, @intFromFloat(self.z * 100.0));
        csum +%= @as(u32, self.status);
        return @as(u16, @truncate(csum));
    }

    pub fn isValid(self: *const TelemetryFrame) bool {
        return self.checksum == self.computeChecksum();
    }
};

/// Shared telemetry ring buffers
pub const TelemetryRingBuffer = RingBuffer(TelemetryFrame, 1024);
pub const CommandBuffer       = RingBuffer(u64, 256);
