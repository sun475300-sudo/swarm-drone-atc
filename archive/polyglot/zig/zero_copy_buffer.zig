// Phase 594: Zero-Copy Ring Buffer — Zig
// 무복사 링 버퍼: 고성능 텔레메트리 스트리밍,
// lock-free 단일 생산자/소비자 큐.

const std = @import("std");
const print = std.debug.print;
const assert = std.debug.assert;

/// 텔레메트리 패킷 구조체
const TelemetryPacket = struct {
    drone_id: u16,
    timestamp: u64,
    latitude: f64,
    longitude: f64,
    altitude: f32,
    speed: f32,
    heading: f32,
    battery_pct: u8,
    flags: u8,

    pub fn format(self: TelemetryPacket) void {
        print("  DRONE_{d:0>3} | alt={d:.1} spd={d:.1} bat={d}%\n", .{
            self.drone_id,
            self.altitude,
            self.speed,
            self.battery_pct,
        });
    }
};

/// Zero-Copy Ring Buffer
/// 단일 생산자, 단일 소비자 (SPSC) lock-free 큐
fn RingBuffer(comptime T: type, comptime capacity: usize) type {
    return struct {
        const Self = @This();

        buffer: [capacity]T = undefined,
        write_idx: usize = 0,
        read_idx: usize = 0,
        count: usize = 0,
        total_written: u64 = 0,
        total_read: u64 = 0,
        overflows: u64 = 0,

        /// 초기화
        pub fn init() Self {
            return Self{};
        }

        /// 쓰기 (생산자)
        pub fn push(self: *Self, item: T) bool {
            if (self.count >= capacity) {
                self.overflows += 1;
                return false; // 버퍼 풀
            }
            self.buffer[self.write_idx] = item;
            self.write_idx = (self.write_idx + 1) % capacity;
            self.count += 1;
            self.total_written += 1;
            return true;
        }

        /// 읽기 (소비자) — 무복사: 포인터 반환
        pub fn peek(self: *Self) ?*const T {
            if (self.count == 0) return null;
            return &self.buffer[self.read_idx];
        }

        /// 소비 확인 (읽기 완료 후 호출)
        pub fn pop(self: *Self) ?T {
            if (self.count == 0) return null;
            const item = self.buffer[self.read_idx];
            self.read_idx = (self.read_idx + 1) % capacity;
            self.count -= 1;
            self.total_read += 1;
            return item;
        }

        /// 벌크 쓰기
        pub fn pushSlice(self: *Self, items: []const T) usize {
            var written: usize = 0;
            for (items) |item| {
                if (!self.push(item)) break;
                written += 1;
            }
            return written;
        }

        /// 현재 상태
        pub fn isEmpty(self: *const Self) bool {
            return self.count == 0;
        }

        pub fn isFull(self: *const Self) bool {
            return self.count >= capacity;
        }

        pub fn available(self: *const Self) usize {
            return capacity - self.count;
        }

        pub fn getCapacity() usize {
            return capacity;
        }

        /// 통계 출력
        pub fn printStats(self: *const Self) void {
            print("=== Ring Buffer Stats ===\n", .{});
            print("  Capacity:      {d}\n", .{capacity});
            print("  Current count: {d}\n", .{self.count});
            print("  Total written: {d}\n", .{self.total_written});
            print("  Total read:    {d}\n", .{self.total_read});
            print("  Overflows:     {d}\n", .{self.overflows});
            print("  Available:     {d}\n", .{self.available()});
        }
    };
}

/// 텔레메트리 링 버퍼 (256 슬롯)
const TelemetryBuffer = RingBuffer(TelemetryPacket, 256);

/// CRC8 체크섬 (간이)
fn crc8(data: []const u8) u8 {
    var crc: u8 = 0xFF;
    for (data) |byte| {
        crc ^= byte;
        var i: u3 = 0;
        while (i < 8) : (i += 1) {
            if (crc & 0x80 != 0) {
                crc = (crc << 1) ^ 0x31;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

/// 메인 시뮬레이션
pub fn main() void {
    print("=== SDACS Zero-Copy Ring Buffer ===\n\n", .{});

    var buf = TelemetryBuffer.init();

    // 텔레메트리 데이터 생산
    print("--- Producing telemetry ---\n", .{});
    var i: u16 = 0;
    while (i < 50) : (i += 1) {
        const packet = TelemetryPacket{
            .drone_id = i % 10,
            .timestamp = @as(u64, i) * 100,
            .latitude = 37.5665 + @as(f64, @floatFromInt(i)) * 0.0001,
            .longitude = 126.978 + @as(f64, @floatFromInt(i)) * 0.0001,
            .altitude = 50.0 + @as(f32, @floatFromInt(i)) * 5.0,
            .speed = 10.0 + @as(f32, @floatFromInt(i % 20)),
            .heading = @as(f32, @floatFromInt(i * 7 % 360)),
            .battery_pct = @intCast(100 - i % 30),
            .flags = 0x01,
        };
        _ = buf.push(packet);
    }
    print("  Produced: {d} packets\n\n", .{buf.total_written});

    // 텔레메트리 데이터 소비 (무복사 peek)
    print("--- Consuming (zero-copy peek) ---\n", .{});
    var consumed: u32 = 0;
    while (!buf.isEmpty()) {
        if (buf.peek()) |pkt| {
            if (consumed < 5) {
                pkt.format();
            }
        }
        _ = buf.pop();
        consumed += 1;
    }
    print("  Consumed: {d} packets\n\n", .{consumed});

    // 통계
    buf.printStats();
}
