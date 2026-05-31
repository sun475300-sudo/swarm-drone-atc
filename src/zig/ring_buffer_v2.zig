// Ring Buffer v2 — SDACS Phase 658
const std = @import("std");

pub fn RingBuffer(comptime T: type, comptime capacity: usize) type {
    return struct {
        data: [capacity]T = undefined,
        head: usize = 0,
        tail: usize = 0,
        pub fn push(self: *@This(), val: T) void { self.data[self.tail] = val; }
    };
}
