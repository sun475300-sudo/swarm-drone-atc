// Phase 654 — Zig Ring Buffer v2 (lock-free FIFO with overwrite)
const std = @import("std");

pub fn RingBuffer(comptime T: type, comptime capacity: usize) type {
    return struct {
        const Self = @This();
        buf: [capacity]T = undefined,
        head: usize = 0,
        tail: usize = 0,
        size: usize = 0,

        pub fn push(self: *Self, item: T) void {
            self.buf[self.head] = item;
            self.head = (self.head + 1) % capacity;
            if (self.size < capacity) { self.size += 1; }
            else { self.tail = (self.tail + 1) % capacity; }
        }

        pub fn pop(self: *Self) ?T {
            if (self.size == 0) return null;
            const item = self.buf[self.tail];
            self.tail = (self.tail + 1) % capacity;
            self.size -= 1;
            return item;
        }

        pub fn len(self: *const Self) usize { return self.size; }
    };
}
