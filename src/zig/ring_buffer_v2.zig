// Phase 644: Ring Buffer v2 — Zig
// SDACS enhanced lock-free ring buffer with batch operations and statistics

const std = @import("std");
const Allocator = std.mem.Allocator;

pub fn RingBufferV2(comptime T: type, comptime Capacity: usize) type {
    comptime if (!std.math.isPowerOfTwo(Capacity)) @compileError("Capacity must be power of 2");

    return struct {
        const Self = @This();
        const MASK = Capacity - 1;

        buffer:    [Capacity]T,
        read_idx:  std.atomic.Value(usize),
        write_idx: std.atomic.Value(usize),
        stat_push: usize,
        stat_pop:  usize,
        stat_drop: usize,

        pub fn init() Self {
            return .{
                .buffer    = undefined,
                .read_idx  = std.atomic.Value(usize).init(0),
                .write_idx = std.atomic.Value(usize).init(0),
                .stat_push = 0,
                .stat_pop  = 0,
                .stat_drop = 0,
            };
        }

        pub fn push(self: *Self, item: T) bool {
            const w = self.write_idx.load(.monotonic);
            const r = self.read_idx.load(.acquire);
            if (w - r >= Capacity) { self.stat_drop += 1; return false; }
            self.buffer[w & MASK] = item;
            self.write_idx.store(w + 1, .release);
            self.stat_push += 1;
            return true;
        }

        pub fn pop(self: *Self) ?T {
            const r = self.read_idx.load(.monotonic);
            const w = self.write_idx.load(.acquire);
            if (r == w) return null;
            const item = self.buffer[r & MASK];
            self.read_idx.store(r + 1, .release);
            self.stat_pop += 1;
            return item;
        }

        pub fn len(self: *const Self) usize {
            const w = self.write_idx.load(.acquire);
            const r = self.read_idx.load(.acquire);
            return w - r;
        }

        pub fn isEmpty(self: *const Self) bool { return self.len() == 0; }
        pub fn isFull(self: *const Self)  bool { return self.len() >= Capacity; }

        pub fn pushBatch(self: *Self, items: []const T) usize {
            var count: usize = 0;
            for (items) |item| { if (self.push(item)) count += 1 else break; }
            return count;
        }

        pub fn popBatch(self: *Self, dest: []T) usize {
            var count: usize = 0;
            while (count < dest.len) {
                if (self.pop()) |item| { dest[count] = item; count += 1; } else break;
            }
            return count;
        }

        pub fn stats(self: *const Self) struct { pushed: usize, popped: usize, dropped: usize } {
            return .{ .pushed = self.stat_push, .popped = self.stat_pop, .dropped = self.stat_drop };
        }
    };
}

test "RingBufferV2 basic" {
    var buf = RingBufferV2(u32, 16).init();
    try std.testing.expect(buf.push(1));
    try std.testing.expect(buf.push(2));
    try std.testing.expectEqual(@as(?u32, 1), buf.pop());
    try std.testing.expectEqual(@as(?u32, 2), buf.pop());
    try std.testing.expect(buf.isEmpty());
}

test "RingBufferV2 batch ops" {
    var buf = RingBufferV2(u8, 8).init();
    const items = [_]u8{ 1, 2, 3, 4, 5 };
    const pushed = buf.pushBatch(&items);
    try std.testing.expectEqual(@as(usize, 5), pushed);

    var out: [5]u8 = undefined;
    const popped = buf.popBatch(&out);
    try std.testing.expectEqual(@as(usize, 5), popped);
    try std.testing.expectEqualSlices(u8, &items, &out);
}
