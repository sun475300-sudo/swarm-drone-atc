// SDACS Ring Buffer V2 — Zig
// 군집드론 링 버퍼 v2 (단순 최적화 버전)

const std = @import("std");

pub fn RingBufferV2(comptime T: type, comptime capacity: usize) type {
    return struct {
        const Self = @This();
        buf: [capacity]T = undefined,
        head: usize = 0,
        tail: usize = 0,
        count: usize = 0,

        pub fn push(self: *Self, item: T) bool {
            if (self.count == capacity) return false;
            self.buf[self.tail] = item;
            self.tail = (self.tail + 1) % capacity;
            self.count += 1;
            return true;
        }

        pub fn pop(self: *Self) ?T {
            if (self.count == 0) return null;
            const item = self.buf[self.head];
            self.head = (self.head + 1) % capacity;
            self.count -= 1;
            return item;
        }

        pub fn len(self: *const Self) usize { return self.count; }
        pub fn isEmpty(self: *const Self) bool { return self.count == 0; }
    };
}

pub fn main() void {
    var rb = RingBufferV2(u32, 16){};
    _ = rb.push(42);
    _ = rb.push(100);
    std.debug.print("RingBufferV2 len: {}\n", .{rb.len()});
}
