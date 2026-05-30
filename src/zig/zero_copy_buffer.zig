// SDACS Zero-Copy Buffer — Zig
// 군집드론 제로카피 링 버퍼

const std = @import("std");
const Allocator = std.mem.Allocator;

/// 링 버퍼 에러 타입
pub const RingBufferError = error{
    BufferFull,
    BufferEmpty,
    InvalidCapacity,
};

/// 제네릭 RingBuffer 구현
pub fn RingBuffer(comptime T: type) type {
    return struct {
        const Self = @This();

        data: []T,
        head: usize,
        tail: usize,
        count: usize,
        capacity: usize,
        allocator: Allocator,

        /// 새 RingBuffer 생성
        pub fn init(allocator: Allocator, capacity: usize) !Self {
            if (capacity == 0) return RingBufferError.InvalidCapacity;
            const data = try allocator.alloc(T, capacity);
            return Self{
                .data = data,
                .head = 0,
                .tail = 0,
                .count = 0,
                .capacity = capacity,
                .allocator = allocator,
            };
        }

        /// 버퍼 해제
        pub fn deinit(self: *Self) void {
            self.allocator.free(self.data);
        }

        /// 데이터 쓰기 (zero-copy push)
        pub fn push(self: *Self, item: T) !void {
            if (self.count == self.capacity) {
                return RingBufferError.BufferFull;
            }
            self.data[self.tail] = item;
            self.tail = (self.tail + 1) % self.capacity;
            self.count += 1;
        }

        /// 데이터 읽기 (zero-copy pop)
        pub fn pop(self: *Self) !T {
            if (self.count == 0) {
                return RingBufferError.BufferEmpty;
            }
            const item = self.data[self.head];
            self.head = (self.head + 1) % self.capacity;
            self.count -= 1;
            return item;
        }

        /// 비파괴적 peek
        pub fn peek(self: *const Self) !T {
            if (self.count == 0) return RingBufferError.BufferEmpty;
            return self.data[self.head];
        }

        pub fn isEmpty(self: *const Self) bool {
            return self.count == 0;
        }

        pub fn isFull(self: *const Self) bool {
            return self.count == self.capacity;
        }

        pub fn len(self: *const Self) usize {
            return self.count;
        }
    };
}

/// 드론 텔레메트리 프레임 타입
pub const TelemetryFrame = struct {
    drone_id: u32,
    timestamp: u64,
    lat: f64,
    lon: f64,
    alt: f32,
    battery: u8,
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var buf = try RingBuffer(TelemetryFrame).init(allocator, 64);
    defer buf.deinit();

    const frame = TelemetryFrame{
        .drone_id = 1,
        .timestamp = 1234567890,
        .lat = 37.5665,
        .lon = 126.978,
        .alt = 100.0,
        .battery = 85,
    };

    try buf.push(frame);
    std.debug.print("Buffer len: {d}\n", .{buf.len()});
    const popped = try buf.pop();
    std.debug.print("Drone ID: {d}\n", .{popped.drone_id});
}
