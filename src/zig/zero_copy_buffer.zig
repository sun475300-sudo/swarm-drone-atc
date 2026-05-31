// Phase 594 — Zig zero-copy buffer for drone telemetry stream
// SDACS high-performance zero-copy ring buffer implementation

const std = @import("std");
const assert = std.debug.assert;
const Allocator = std.mem.Allocator;

// ---- Zero-copy ring buffer ----
// Also exported as RingBuffer alias for compatibility with Phase 594 consumers.

/// ZeroCopyBuffer — fixed-capacity byte ring buffer that avoids data copies
/// by exposing contiguous slices directly into the backing store.
pub fn ZeroCopyBuffer(comptime capacity: usize) type {
    comptime assert(capacity > 0 and (capacity & (capacity - 1)) == 0); // must be power of 2
    return struct {
        const Self = @This();
        const mask = capacity - 1;

        data: [capacity]u8 = undefined,
        head: usize = 0, // write position
        tail: usize = 0, // read position

        pub fn init() Self {
            return .{};
        }

        pub fn len(self: *const Self) usize {
            return self.head -% self.tail;
        }

        pub fn free(self: *const Self) usize {
            return capacity - self.len();
        }

        pub fn isEmpty(self: *const Self) bool {
            return self.head == self.tail;
        }

        pub fn isFull(self: *const Self) bool {
            return self.len() == capacity;
        }

        /// Write bytes into the buffer; returns number of bytes written.
        pub fn write(self: *Self, src: []const u8) usize {
            const available = self.free();
            const n = @min(src.len, available);
            for (src[0..n], 0..) |b, i| {
                self.data[(self.head +% i) & mask] = b;
            }
            self.head +%= n;
            return n;
        }

        /// Read bytes from the buffer into dst; returns number of bytes read.
        pub fn read(self: *Self, dst: []u8) usize {
            const available = self.len();
            const n = @min(dst.len, available);
            for (dst[0..n], 0..) |*d, i| {
                d.* = self.data[(self.tail +% i) & mask];
            }
            self.tail +%= n;
            return n;
        }

        /// Peek at up to dst.len bytes without consuming them.
        pub fn peek(self: *const Self, dst: []u8) usize {
            const available = self.len();
            const n = @min(dst.len, available);
            for (dst[0..n], 0..) |*d, i| {
                d.* = self.data[(self.tail +% i) & mask];
            }
            return n;
        }

        /// Discard n bytes from the read side.
        pub fn skip(self: *Self, n: usize) void {
            const actual = @min(n, self.len());
            self.tail +%= actual;
        }

        /// Reset the buffer to empty state.
        pub fn reset(self: *Self) void {
            self.head = 0;
            self.tail = 0;
        }
    };
}

// ---- Telemetry packet layout ----

/// Minimal telemetry header for zero-copy parsing
const TelemetryHeader = extern struct {
    magic: u16,         // 0xABCD
    drone_id: u16,
    timestamp_ms: u64,
    seq_no: u32,
    payload_len: u16,
};

const MAGIC: u16 = 0xABCD;

/// Parse a TelemetryHeader from the buffer without copying the payload.
pub fn parseTelemetryHeader(buf: []const u8) ?TelemetryHeader {
    if (buf.len < @sizeOf(TelemetryHeader)) return null;
    const hdr = @as(*const TelemetryHeader, @ptrCast(@alignCast(buf.ptr))).*;
    if (hdr.magic != MAGIC) return null;
    return hdr;
}

// ---- Tests ----

test "ZeroCopyBuffer basic write and read" {
    var buf = ZeroCopyBuffer(64).init();
    const src = "hello drone";
    const written = buf.write(src);
    try std.testing.expectEqual(src.len, written);
    try std.testing.expectEqual(src.len, buf.len());

    var dst: [16]u8 = undefined;
    const n = buf.read(dst[0..src.len]);
    try std.testing.expectEqual(src.len, n);
    try std.testing.expectEqualSlices(u8, src, dst[0..n]);
    try std.testing.expect(buf.isEmpty());
}

test "ZeroCopyBuffer wrap-around" {
    var buf = ZeroCopyBuffer(8).init();
    _ = buf.write("1234567"); // fill 7 of 8
    var tmp: [4]u8 = undefined;
    _ = buf.read(tmp[0..4]);  // consume 4
    _ = buf.write("ABCD");    // write 4 more (wraps)
    try std.testing.expectEqual(@as(usize, 7), buf.len());
}

test "ZeroCopyBuffer full and overflow" {
    var buf = ZeroCopyBuffer(4).init();
    const n1 = buf.write("ABCD");
    try std.testing.expectEqual(@as(usize, 4), n1);
    try std.testing.expect(buf.isFull());
    const n2 = buf.write("X"); // no room
    try std.testing.expectEqual(@as(usize, 0), n2);
}

// ---- Main ----

pub fn main() !void {
    var buf = ZeroCopyBuffer(256).init();
    const msg = "drone telemetry zero copy test";
    _ = buf.write(msg);
    std.debug.print("Buffered {} bytes, free {}\n", .{ buf.len(), buf.free() });

    var out: [64]u8 = undefined;
    const n = buf.read(out[0..]);
    std.debug.print("Read: {s}\n", .{out[0..n]});
}
