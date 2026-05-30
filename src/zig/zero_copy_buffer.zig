// Phase 594: zero_copy_buffer — Zig 기반 제로 카피 링 버퍼
// SDACS Zero-Copy RingBuffer for High-Performance Telemetry

const std = @import("std");
const assert = std.debug.assert;
const mem = std.mem;

// 제로 카피 링 버퍼 (RingBuffer)
pub fn RingBuffer(comptime T: type, comptime capacity: usize) type {
    comptime {
        // capacity는 2의 거듭제곱이어야 함 (마스크 연산 최적화)
        assert(capacity > 0 and (capacity & (capacity - 1)) == 0);
    }

    return struct {
        const Self = @This();
        const MASK = capacity - 1;

        buf:   [capacity]T = undefined,
        head:  usize = 0,  // 읽기 포인터
        tail:  usize = 0,  // 쓰기 포인터
        count: usize = 0,

        pub fn init() Self {
            return .{};
        }

        pub fn len(self: *const Self) usize {
            return self.count;
        }

        pub fn isEmpty(self: *const Self) bool {
            return self.count == 0;
        }

        pub fn isFull(self: *const Self) bool {
            return self.count == capacity;
        }

        pub fn available(self: *const Self) usize {
            return capacity - self.count;
        }

        // 제로 카피 쓰기 — 포인터 반환
        pub fn writeSlot(self: *Self) ?*T {
            if (self.isFull()) return null;
            const slot = &self.buf[self.tail & MASK];
            self.tail +%= 1;
            self.count += 1;
            return slot;
        }

        // 단일 항목 쓰기
        pub fn push(self: *Self, item: T) bool {
            if (self.isFull()) return false;
            self.buf[self.tail & MASK] = item;
            self.tail +%= 1;
            self.count += 1;
            return true;
        }

        // 제로 카피 읽기 — 포인터 반환 (복사 없음)
        pub fn peekSlot(self: *Self) ?*const T {
            if (self.isEmpty()) return null;
            return &self.buf[self.head & MASK];
        }

        // 항목 소비 (읽기 포인터 전진)
        pub fn pop(self: *Self) ?T {
            if (self.isEmpty()) return null;
            const item = self.buf[self.head & MASK];
            self.head +%= 1;
            self.count -= 1;
            return item;
        }

        // 배치 읽기 (연속 슬라이스, 제로 카피)
        pub fn peekContiguous(self: *Self, max_items: usize) []const T {
            if (self.isEmpty()) return &[_]T{};
            const avail = @min(self.count, max_items);
            const start = self.head & MASK;
            const end   = @min(start + avail, capacity);
            return self.buf[start..end];
        }

        // 배치 소비
        pub fn drain(self: *Self, n: usize) void {
            const actual = @min(n, self.count);
            self.head +%= actual;
            self.count -= actual;
        }

        pub fn clear(self: *Self) void {
            self.head  = 0;
            self.tail  = 0;
            self.count = 0;
        }
    };
}

// 드론 텔레메트리 패킷
const TelemetryPacket = struct {
    drone_id  : u32,
    timestamp : u64,
    lat       : f64,
    lon       : f64,
    alt       : f32,
    battery   : f32,
    crc       : u32,

    pub fn computeCRC(self: *const @This()) u32 {
        var crc: u32 = 0xFFFFFFFF;
        crc ^= self.drone_id;
        crc ^= @as(u32, @truncate(self.timestamp));
        crc ^= @as(u32, @bitCast(@as(f32, @floatCast(self.lat))));
        return ~crc;
    }
};

// 멀티 드론 텔레메트리 링 버퍼
const TelemetryRingBuffer = RingBuffer(TelemetryPacket, 64);

fn simulateTelemetry(buf: *TelemetryRingBuffer, drone_id: u32, t: u64) void {
    const lat: f64 = 37.5 + @as(f64, @floatFromInt(drone_id)) * 0.001;
    const lon: f64 = 127.0 + @as(f64, @floatFromInt(t % 100)) * 0.0001;
    var pkt = TelemetryPacket{
        .drone_id  = drone_id,
        .timestamp = t,
        .lat       = lat,
        .lon       = lon,
        .alt       = 50.0 + @as(f32, @floatFromInt(t % 20)),
        .battery   = 95.0 - @as(f32, @floatFromInt(t)) * 0.01,
        .crc       = 0,
    };
    pkt.crc = pkt.computeCRC();
    _ = buf.push(pkt);
}

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    try stdout.print("SDACS Zero-Copy RingBuffer — Phase 594\n\n", .{});

    var buf = TelemetryRingBuffer.init();
    try stdout.print("RingBuffer 용량: {d} 패킷\n", .{64});

    // 시뮬레이션 데이터 삽입
    var t: u64 = 0;
    while (t < 10) : (t += 1) {
        for (0..5) |drone_id| {
            simulateTelemetry(&buf, @intCast(drone_id), t);
        }
    }

    try stdout.print("버퍼 상태: {d}/{d} 패킷\n", .{ buf.len(), 64 });

    // 제로 카피 읽기 (배치)
    try stdout.print("\n제로 카피 배치 읽기:\n", .{});
    var read_count: usize = 0;
    while (!buf.isEmpty() and read_count < 5) {
        if (buf.pop()) |pkt| {
            try stdout.print("  드론{d} t={d}: alt={d:.1}m bat={d:.1}%\n",
                .{ pkt.drone_id, pkt.timestamp, pkt.alt, pkt.battery });
            read_count += 1;
        }
    }

    try stdout.print("\n남은 버퍼 항목: {d}\n", .{buf.len()});
    try stdout.print("링 버퍼 처리 완료.\n", .{});
}
