// Ring buffer v2 stub for SDACS telemetry queue — Zig
const std = @import("std");

pub fn RingBuffer(comptime T: type, comptime capacity: usize) type {
    return struct {
        const Self = @This();
        buf: [capacity]T = undefined,
        head: usize = 0,
        tail: usize = 0,
        len: usize = 0,

        pub fn push(self: *Self, value: T) bool {
            if (self.len == capacity) return false;
            self.buf[self.tail] = value;
            self.tail = (self.tail + 1) % capacity;
            self.len += 1;
            return true;
        }

        pub fn pop(self: *Self) ?T {
            if (self.len == 0) return null;
            const value = self.buf[self.head];
            self.head = (self.head + 1) % capacity;
            self.len -= 1;
            return value;
        }
    };
}
