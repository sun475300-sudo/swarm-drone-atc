// Phase 654 — Lock-free Ring Buffer v2 in Zig
const std = @import("std");
const Atomic = std.atomic.Atomic;

pub fn RingBuffer(comptime T: type, comptime N: usize) type {
    return struct {
        buf: [N]T = undefined,
        head: Atomic(usize) = Atomic(usize).init(0),
        tail: Atomic(usize) = Atomic(usize).init(0),

        const Self = @This();

        pub fn push(self: *Self, item: T) void {
            const tail = self.tail.load(.Monotonic);
            self.buf[tail % N] = item;
            self.tail.store(tail + 1, .Release);
        }

        pub fn pop(self: *Self) ?T {
            const head = self.head.load(.Monotonic);
            const tail = self.tail.load(.Acquire);
            if (head == tail) return null;
            const item = self.buf[head % N];
            self.head.store(head + 1, .Release);
            return item;
        }

        pub fn len(self: *Self) usize {
            return self.tail.load(.Monotonic) - self.head.load(.Monotonic);
        }
    };
}
