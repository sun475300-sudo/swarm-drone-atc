// Zero-copy Ring Buffer — SDACS Phase 594
// Lock-free ring buffer for telemetry streaming

const std = @import("std");
const Atomic = std.atomic.Value;

pub fn RingBuffer(comptime T: type, comptime capacity: usize) type {
    comptime {
        if (!std.math.isPowerOfTwo(capacity))
            @compileError("capacity must be a power of two");
    }
    return struct {
        const Self = @This();
        const MASK = capacity - 1;

        data  : [capacity]T = undefined,
        head  : Atomic(usize) = Atomic(usize).init(0),
        tail  : Atomic(usize) = Atomic(usize).init(0),

        pub fn push(self: *Self, val: T) bool {
            const tail = self.tail.load(.acquire);
            const next = (tail + 1) & MASK;
            if (next == self.head.load(.acquire)) return false; // full
            self.data[tail] = val;
            self.tail.store(next, .release);
            return true;
        }

        pub fn pop(self: *Self) ?T {
            const head = self.head.load(.acquire);
            if (head == self.tail.load(.acquire)) return null; // empty
            const val = self.data[head];
            self.head.store((head + 1) & MASK, .release);
            return val;
        }

        pub fn len(self: *const Self) usize {
            const h = self.head.load(.monotonic);
            const t = self.tail.load(.monotonic);
            return (t -% h) & MASK;
        }

        pub fn isEmpty(self: *const Self) bool {
            return self.head.load(.monotonic) == self.tail.load(.monotonic);
        }
    };
}
// end
// end
// end
// end
// end
