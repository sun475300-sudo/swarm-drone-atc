// P654: Ring Buffer v2 - Zig stub
// Lock-free ring buffer for drone telemetry streaming

const std = @import("std");

pub fn RingBuffer(comptime T: type, comptime capacity: usize) type {
    return struct {
        const Self = @This();
        const Capacity = capacity;

        data: [Capacity]T = undefined,
        head: usize = 0,
        tail: usize = 0,
        count: usize = 0,

        pub fn push(self: *Self, item: T) bool {
            if (self.count == Capacity) return false;
            self.data[self.tail] = item;
            self.tail = (self.tail + 1) % Capacity;
            self.count += 1;
            return true;
        }

        pub fn pop(self: *Self) ?T {
            if (self.count == 0) return null;
            const item = self.data[self.head];
            self.head = (self.head + 1) % Capacity;
            self.count -= 1;
            return item;
        }

        pub fn peek(self: *const Self) ?T {
            if (self.count == 0) return null;
            return self.data[self.head];
        }

        pub fn len(self: *const Self) usize {
            return self.count;
        }

        pub fn isEmpty(self: *const Self) bool {
            return self.count == 0;
        }

        pub fn isFull(self: *const Self) bool {
            return self.count == Capacity;
        }
    };
}

pub const TelemetryFrame = struct {
    drone_id: u32,
    timestamp_ms: u64,
    x: f32,
    y: f32,
    z: f32,
    battery: f32,
};

pub const TelemetryBuffer = RingBuffer(TelemetryFrame, 512);
