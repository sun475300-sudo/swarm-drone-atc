// Phase 584: Zero-Copy Ring Buffer — Zig
// SDACS lock-free ring buffer for drone telemetry streaming

const std = @import("std");
const Allocator = std.mem.Allocator;
const assert = std.debug.assert;

/// Lock-free single-producer single-consumer ring buffer
/// Uses power-of-2 capacity for efficient masking
pub fn RingBuffer(comptime T: type) type {
    return struct {
        const Self = @This();

        buffer   : []T,
        capacity : usize,
        mask     : usize,
        read_idx : std.atomic.Value(usize),
        write_idx: std.atomic.Value(usize),
        alloc    : Allocator,

        pub fn init(alloc: Allocator, capacity: usize) !Self {
            // Round up to next power of 2
            var cap = capacity;
            if (cap == 0) cap = 1;
            if (!std.math.isPowerOfTwo(cap)) {
                cap = std.math.ceilPowerOfTwo(usize, cap) catch return error.Overflow;
            }

            const buf = try alloc.alloc(T, cap);
            return Self{
                .buffer    = buf,
                .capacity  = cap,
                .mask      = cap - 1,
                .read_idx  = std.atomic.Value(usize).init(0),
                .write_idx = std.atomic.Value(usize).init(0),
                .alloc     = alloc,
            };
        }

        pub fn deinit(self: *Self) void {
            self.alloc.free(self.buffer);
        }

        /// Push an item. Returns false if buffer is full.
        pub fn push(self: *Self, item: T) bool {
            const write = self.write_idx.load(.monotonic);
            const read  = self.read_idx.load(.acquire);
            if (write - read >= self.capacity) return false;

            self.buffer[write & self.mask] = item;
            self.write_idx.store(write + 1, .release);
            return true;
        }

        /// Pop an item. Returns null if buffer is empty.
        pub fn pop(self: *Self) ?T {
            const read  = self.read_idx.load(.monotonic);
            const write = self.write_idx.load(.acquire);
            if (read == write) return null;

            const item = self.buffer[read & self.mask];
            self.read_idx.store(read + 1, .release);
            return item;
        }

        /// Peek at the next item without consuming it.
        pub fn peek(self: *const Self) ?T {
            const read  = self.read_idx.load(.monotonic);
            const write = self.write_idx.load(.acquire);
            if (read == write) return null;
            return self.buffer[read & self.mask];
        }

        /// Number of items currently in buffer
        pub fn len(self: *const Self) usize {
            const write = self.write_idx.load(.acquire);
            const read  = self.read_idx.load(.acquire);
            return write - read;
        }

        pub fn isEmpty(self: *const Self) bool {
            return self.len() == 0;
        }

        pub fn isFull(self: *const Self) bool {
            return self.len() >= self.capacity;
        }

        pub fn availableSpace(self: *const Self) usize {
            return self.capacity - self.len();
        }

        /// Drain up to max_items into a slice, returns count drained
        pub fn drain(self: *Self, dest: []T) usize {
            var count: usize = 0;
            while (count < dest.len) {
                if (self.pop()) |item| {
                    dest[count] = item;
                    count += 1;
                } else break;
            }
            return count;
        }

        /// Fill buffer from a slice, returns count pushed
        pub fn fill(self: *Self, src: []const T) usize {
            var count: usize = 0;
            for (src) |item| {
                if (!self.push(item)) break;
                count += 1;
            }
            return count;
        }

        pub fn reset(self: *Self) void {
            self.read_idx.store(0, .release);
            self.write_idx.store(0, .release);
        }
    };
}

/// Telemetry frame for drone data
pub const TelemetryFrame = extern struct {
    drone_id  : u16,
    timestamp : u64,
    lat       : f32,
    lon       : f32,
    alt       : f32,
    speed     : f32,
    heading   : f32,
    battery   : f32,
    sequence  : u32,
    _pad      : u32 = 0,
};

/// Telemetry ring buffer with statistics
pub const TelemetryBuffer = struct {
    ring      : RingBuffer(TelemetryFrame),
    pushed    : usize,
    dropped   : usize,
    consumed  : usize,

    pub fn init(alloc: Allocator, capacity: usize) !TelemetryBuffer {
        return TelemetryBuffer{
            .ring    = try RingBuffer(TelemetryFrame).init(alloc, capacity),
            .pushed  = 0,
            .dropped = 0,
            .consumed = 0,
        };
    }

    pub fn deinit(self: *TelemetryBuffer) void {
        self.ring.deinit();
    }

    pub fn write(self: *TelemetryBuffer, frame: TelemetryFrame) void {
        if (self.ring.push(frame)) {
            self.pushed += 1;
        } else {
            self.dropped += 1;
        }
    }

    pub fn read(self: *TelemetryBuffer) ?TelemetryFrame {
        const frame = self.ring.pop();
        if (frame != null) self.consumed += 1;
        return frame;
    }

    pub fn stats(self: *const TelemetryBuffer) void {
        std.debug.print("TelemetryBuffer: pushed={} dropped={} consumed={} buffered={}\n",
            .{ self.pushed, self.dropped, self.consumed, self.ring.len() });
    }
};

test "RingBuffer basic push/pop" {
    var buf = try RingBuffer(u32).init(std.testing.allocator, 8);
    defer buf.deinit();

    try std.testing.expect(buf.isEmpty());
    try std.testing.expect(buf.push(42));
    try std.testing.expect(!buf.isEmpty());
    try std.testing.expectEqual(@as(?u32, 42), buf.pop());
    try std.testing.expect(buf.isEmpty());
}

test "RingBuffer overflow" {
    var buf = try RingBuffer(u8).init(std.testing.allocator, 4);
    defer buf.deinit();

    for (0..4) |i| {
        try std.testing.expect(buf.push(@intCast(i)));
    }
    try std.testing.expect(!buf.push(99));  // full
    try std.testing.expect(buf.isFull());
}

test "TelemetryFrame size" {
    try std.testing.expect(@sizeOf(TelemetryFrame) == 40);
}
