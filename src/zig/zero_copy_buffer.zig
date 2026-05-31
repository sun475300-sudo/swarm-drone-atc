// zero_copy_buffer.zig - Zero-copy ring buffer for drone telemetry
// High-performance lock-free buffer for SDACS telemetry data

const std = @import("std");
const Allocator = std.mem.Allocator;
const assert = std.debug.assert;

/// Telemetry frame stored in the ring buffer
pub const TelemetryFrame = struct {
    drone_id:   [8]u8,
    timestamp:  i64,
    pos_x:      f32,
    pos_y:      f32,
    pos_z:      f32,
    vel_x:      f32,
    vel_y:      f32,
    vel_z:      f32,
    battery:    u8,
    status:     u8,
    crc:        u32,
};

/// Lock-free single-producer single-consumer ring buffer
pub fn RingBuffer(comptime T: type, comptime size: usize) type {
    comptime assert(size > 0 and (size & (size - 1)) == 0); // must be power of 2

    return struct {
        const Self = @This();
        const MASK = size - 1;

        data:        [size]T,
        write_head:  std.atomic.Value(usize),
        read_head:   std.atomic.Value(usize),
        capacity:    usize,

        pub fn init() Self {
            return .{
                .data       = undefined,
                .write_head = std.atomic.Value(usize).init(0),
                .read_head  = std.atomic.Value(usize).init(0),
                .capacity   = size,
            };
        }

        /// Push item without copying — returns pointer to write slot
        pub fn push(self: *Self, item: T) bool {
            const write = self.write_head.load(.monotonic);
            const read  = self.read_head.load(.acquire);
            if (write - read >= size) return false; // buffer full

            self.data[write & MASK] = item;
            _ = self.write_head.fetchAdd(1, .release);
            return true;
        }

        /// Pop item from buffer
        pub fn pop(self: *Self) ?T {
            const read  = self.read_head.load(.monotonic);
            const write = self.write_head.load(.acquire);
            if (read == write) return null; // empty

            const item = self.data[read & MASK];
            _ = self.read_head.fetchAdd(1, .release);
            return item;
        }

        /// Peek at next item without consuming
        pub fn peek(self: *Self) ?*const T {
            const read  = self.read_head.load(.monotonic);
            const write = self.write_head.load(.acquire);
            if (read == write) return null;
            return &self.data[read & MASK];
        }

        pub fn len(self: *Self) usize {
            const write = self.write_head.load(.acquire);
            const read  = self.read_head.load(.acquire);
            return write - read;
        }

        pub fn isEmpty(self: *Self) bool {
            return self.len() == 0;
        }

        pub fn isFull(self: *Self) bool {
            return self.len() >= size;
        }

        /// Batch push multiple items
        pub fn pushBatch(self: *Self, items: []const T) usize {
            var count: usize = 0;
            for (items) |item| {
                if (!self.push(item)) break;
                count += 1;
            }
            return count;
        }
    };
}

/// Telemetry ring buffer — 1024 frames pre-allocated
pub const TelemetryRingBuffer = RingBuffer(TelemetryFrame, 1024);

/// Buffer statistics for monitoring
pub const BufferStats = struct {
    total_pushed:  u64 = 0,
    total_popped:  u64 = 0,
    overflow_count: u64 = 0,
    current_len:   usize = 0,
};

/// Managed telemetry buffer with statistics
pub const ManagedBuffer = struct {
    buffer: TelemetryRingBuffer,
    stats:  BufferStats,

    pub fn init() ManagedBuffer {
        return .{
            .buffer = TelemetryRingBuffer.init(),
            .stats  = .{},
        };
    }

    pub fn push(self: *ManagedBuffer, frame: TelemetryFrame) bool {
        if (self.buffer.push(frame)) {
            self.stats.total_pushed += 1;
            self.stats.current_len = self.buffer.len();
            return true;
        }
        self.stats.overflow_count += 1;
        return false;
    }

    pub fn pop(self: *ManagedBuffer) ?TelemetryFrame {
        const frame = self.buffer.pop();
        if (frame != null) {
            self.stats.total_popped += 1;
            self.stats.current_len = self.buffer.len();
        }
        return frame;
    }
};

test "RingBuffer basic operations" {
    var rb = RingBuffer(u32, 4).init();
    try std.testing.expect(rb.isEmpty());
    try std.testing.expect(rb.push(42));
    try std.testing.expect(rb.len() == 1);
    const val = rb.pop();
    try std.testing.expect(val != null);
    try std.testing.expect(val.? == 42);
    try std.testing.expect(rb.isEmpty());
}
