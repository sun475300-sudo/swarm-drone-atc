// Phase 654 — Ring Buffer v2 (Zig)
// 드론 텔레메트리 고성능 링 버퍼 (lock-free, 컴파일 타임 크기)

const std = @import("std");

/// 컴파일 타임 크기 T의 lock-free SPSC 링 버퍼.
pub fn RingBuffer(comptime T: type, comptime capacity: usize) type {
    comptime {
        // capacity는 2의 거듭제곱이어야 한다.
        std.debug.assert(capacity > 0 and (capacity & (capacity - 1)) == 0);
    }

    return struct {
        const Self = @This();
        const mask: usize = capacity - 1;

        buf: [capacity]T = undefined,
        head: usize = 0,  // 소비자가 읽을 인덱스
        tail: usize = 0,  // 생산자가 쓸 인덱스

        /// 아이템을 버퍼에 추가한다. 가득 차면 false를 반환한다.
        pub fn push(self: *Self, item: T) bool {
            const next_tail = (self.tail + 1) & mask;
            if (next_tail == self.head) return false;  // full
            self.buf[self.tail] = item;
            self.tail = next_tail;
            return true;
        }

        /// 아이템을 꺼낸다. 비어 있으면 null을 반환한다.
        pub fn pop(self: *Self) ?T {
            if (self.head == self.tail) return null;  // empty
            const item = self.buf[self.head];
            self.head = (self.head + 1) & mask;
            return item;
        }

        /// 현재 저장된 아이템 수를 반환한다.
        pub fn len(self: *const Self) usize {
            return (self.tail -% self.head) & mask;
        }

        pub fn is_empty(self: *const Self) bool {
            return self.head == self.tail;
        }

        pub fn is_full(self: *const Self) bool {
            return ((self.tail + 1) & mask) == self.head;
        }
    };
}

/// 텔레메트리 프레임 타입.
pub const TelemetryFrame = struct {
    drone_id: u16,
    timestamp_ms: u64,
    x: f32,
    y: f32,
    z: f32,
    vx: f32,
    vy: f32,
    vz: f32,
    battery_pct: f32,
};

// 1024-slot 텔레메트리 링 버퍼
pub const TelemetryRingBuffer = RingBuffer(TelemetryFrame, 1024);
