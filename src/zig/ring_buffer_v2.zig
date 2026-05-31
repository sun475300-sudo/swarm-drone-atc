// ring_buffer_v2.zig - Ring buffer v2 for SDACS telemetry
const std = @import("std");

pub fn RingBuffer(comptime T: type, comptime cap: usize) type {
    return struct {
        const Self = @This();
        data: [cap]T = undefined,
        head: usize = 0,
        tail: usize = 0,
        count: usize = 0,

        pub fn push(self: *Self, item: T) bool {
            if (self.count == cap) return false;
            self.data[self.tail] = item;
            self.tail = (self.tail + 1) % cap;
            self.count += 1;
            return true;
        }

        pub fn pop(self: *Self) ?T {
            if (self.count == 0) return null;
            const item = self.data[self.head];
            self.head = (self.head + 1) % cap;
            self.count -= 1;
            return item;
        }

        pub fn len(self: *const Self) usize { return self.count; }
        pub fn isEmpty(self: *const Self) bool { return self.count == 0; }
        pub fn isFull(self: *const Self) bool { return self.count == cap; }
    };
}
