// Package commbroker implements the SDACS drone communication broker.
//
// 드론 ↔ 관제 간 메시지 라우팅, 큐잉, QoS 관리.
// Go의 goroutine + channel 기반 고성능 동시성 처리.
//
// 기능:
//   - 드론 등록/해제
//   - 우선순위 기반 메시지 큐 (4단계)
//   - 토픽 기반 pub/sub
//   - 메시지 TTL 관리
//   - 처리량/지연 메트릭 수집
//   - gRPC 서비스 인터페이스

package commbroker

import (
	"fmt"
	"math"
	"sort"
	"sync"
	"time"
)

// ── 메시지 타입 ─────────────────────────────────────────

// Priority 메시지 우선순위
type Priority int

const (
	PriorityEmergency Priority = 0 // 비상 (즉시 처리)
	PriorityHigh      Priority = 1 // 높음 (충돌 경보)
	PriorityNormal    Priority = 2 // 보통 (텔레메트리)
	PriorityLow       Priority = 3 // 낮음 (로그)
)

// Message 브로커 메시지
type Message struct {
	ID        string
	Source    string
	Target    string // "*" = broadcast
	Topic     string
	Priority  Priority
	Payload   []byte
	Timestamp time.Time
	TTL       time.Duration
	Retries   int
}

// DroneInfo 등록된 드론 정보
type DroneInfo struct {
	DroneID      string
	LastSeen     time.Time
	MessageCount int64
	BytesSent    int64
	BytesRecv    int64
	Latency      float64 // ms (이동 평균)
	Connected    bool
	Topics       map[string]bool
}

// BrokerMetrics 브로커 메트릭
type BrokerMetrics struct {
	TotalMessages    int64
	TotalBytes       int64
	DroppedMessages  int64
	AvgLatencyMs     float64
	P99LatencyMs     float64
	ActiveDrones     int
	QueueDepth       int
	Throughput       float64 // msg/sec
	UptimeSeconds    float64
}

// ── 브로커 구현 ─────────────────────────────────────────

// CommBroker 드론 통신 브로커
type CommBroker struct {
	mu            sync.RWMutex
	drones        map[string]*DroneInfo
	subscribers   map[string][]chan Message // topic → subscriber channels
	queue         []Message                // 우선순위 정렬 대기열
	maxQueueSize  int
	metrics       BrokerMetrics
	startTime     time.Time
	latencies     []float64 // 최근 1000개
	messageSeq    int64
}

// NewCommBroker 브로커 생성
func NewCommBroker(maxQueueSize int) *CommBroker {
	return &CommBroker{
		drones:       make(map[string]*DroneInfo),
		subscribers:  make(map[string][]chan Message),
		queue:        make([]Message, 0, maxQueueSize),
		maxQueueSize: maxQueueSize,
		startTime:    time.Now(),
		latencies:    make([]float64, 0, 1000),
	}
}

// RegisterDrone 드론 등록
func (b *CommBroker) RegisterDrone(droneID string) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	if _, exists := b.drones[droneID]; exists {
		return fmt.Errorf("drone %s already registered", droneID)
	}

	b.drones[droneID] = &DroneInfo{
		DroneID:   droneID,
		LastSeen:  time.Now(),
		Connected: true,
		Topics:    make(map[string]bool),
	}
	b.metrics.ActiveDrones++
	return nil
}

// UnregisterDrone 드론 해제
func (b *CommBroker) UnregisterDrone(droneID string) {
	b.mu.Lock()
	defer b.mu.Unlock()

	if drone, exists := b.drones[droneID]; exists {
		drone.Connected = false
		b.metrics.ActiveDrones--
	}
}

// Subscribe 토픽 구독
func (b *CommBroker) Subscribe(topic string, bufSize int) chan Message {
	b.mu.Lock()
	defer b.mu.Unlock()

	ch := make(chan Message, bufSize)
	b.subscribers[topic] = append(b.subscribers[topic], ch)
	return ch
}

// Publish 메시지 발행
func (b *CommBroker) Publish(msg Message) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	// TTL 체크
	if !msg.Timestamp.IsZero() && time.Since(msg.Timestamp) > msg.TTL && msg.TTL > 0 {
		b.metrics.DroppedMessages++
		return fmt.Errorf("message expired (TTL: %v)", msg.TTL)
	}

	// 시퀀스 번호 부여
	b.messageSeq++
	msg.ID = fmt.Sprintf("msg_%d", b.messageSeq)

	// 소스 드론 메트릭 업데이트
	if drone, exists := b.drones[msg.Source]; exists {
		drone.LastSeen = time.Now()
		drone.MessageCount++
		drone.BytesSent += int64(len(msg.Payload))
	}

	// 메트릭 업데이트
	b.metrics.TotalMessages++
	b.metrics.TotalBytes += int64(len(msg.Payload))

	// 지연 시간 기록
	if !msg.Timestamp.IsZero() {
		latency := float64(time.Since(msg.Timestamp).Microseconds()) / 1000.0
		b.recordLatency(latency)
	}

	// 브로드캐스트
	if msg.Target == "*" {
		return b.broadcastLocked(msg)
	}

	// 토픽 기반 라우팅
	if msg.Topic != "" {
		return b.publishToTopicLocked(msg)
	}

	// 직접 전송 (큐에 추가)
	return b.enqueueLocked(msg)
}

func (b *CommBroker) broadcastLocked(msg Message) error {
	for _, drone := range b.drones {
		if drone.DroneID != msg.Source && drone.Connected {
			drone.BytesRecv += int64(len(msg.Payload))
		}
	}
	// 모든 토픽 구독자에게 전송
	for _, subs := range b.subscribers {
		for _, ch := range subs {
			select {
			case ch <- msg:
			default:
				b.metrics.DroppedMessages++
			}
		}
	}
	return nil
}

func (b *CommBroker) publishToTopicLocked(msg Message) error {
	subs, exists := b.subscribers[msg.Topic]
	if !exists || len(subs) == 0 {
		return nil
	}

	for _, ch := range subs {
		select {
		case ch <- msg:
		default:
			b.metrics.DroppedMessages++
		}
	}
	return nil
}

func (b *CommBroker) enqueueLocked(msg Message) error {
	if len(b.queue) >= b.maxQueueSize {
		// 최저 우선순위 메시지 제거
		if msg.Priority < b.queue[len(b.queue)-1].Priority {
			b.queue = b.queue[:len(b.queue)-1]
			b.metrics.DroppedMessages++
		} else {
			b.metrics.DroppedMessages++
			return fmt.Errorf("queue full, message dropped")
		}
	}

	b.queue = append(b.queue, msg)
	sort.SliceStable(b.queue, func(i, j int) bool {
		return b.queue[i].Priority < b.queue[j].Priority
	})
	return nil
}

func (b *CommBroker) recordLatency(latencyMs float64) {
	b.latencies = append(b.latencies, latencyMs)
	if len(b.latencies) > 1000 {
		b.latencies = b.latencies[len(b.latencies)-1000:]
	}
}

// DequeueNext 큐에서 다음 메시지 꺼내기
func (b *CommBroker) DequeueNext() *Message {
	b.mu.Lock()
	defer b.mu.Unlock()

	if len(b.queue) == 0 {
		return nil
	}

	msg := b.queue[0]
	b.queue = b.queue[1:]
	return &msg
}

// Heartbeat 드론 하트비트 처리
func (b *CommBroker) Heartbeat(droneID string) {
	b.mu.Lock()
	defer b.mu.Unlock()

	if drone, exists := b.drones[droneID]; exists {
		drone.LastSeen = time.Now()
		drone.Connected = true
	}
}

// PruneDisconnected 비활성 드론 정리 (타임아웃)
func (b *CommBroker) PruneDisconnected(timeout time.Duration) int {
	b.mu.Lock()
	defer b.mu.Unlock()

	pruned := 0
	now := time.Now()
	for _, drone := range b.drones {
		if drone.Connected && now.Sub(drone.LastSeen) > timeout {
			drone.Connected = false
			b.metrics.ActiveDrones--
			pruned++
		}
	}
	return pruned
}

// GetMetrics 메트릭 조회
func (b *CommBroker) GetMetrics() BrokerMetrics {
	b.mu.RLock()
	defer b.mu.RUnlock()

	m := b.metrics
	m.QueueDepth = len(b.queue)
	m.UptimeSeconds = time.Since(b.startTime).Seconds()

	if m.UptimeSeconds > 0 {
		m.Throughput = float64(m.TotalMessages) / m.UptimeSeconds
	}

	if len(b.latencies) > 0 {
		// 평균 지연
		sum := 0.0
		for _, l := range b.latencies {
			sum += l
		}
		m.AvgLatencyMs = sum / float64(len(b.latencies))

		// P99 지연
		sorted := make([]float64, len(b.latencies))
		copy(sorted, b.latencies)
		sort.Float64s(sorted)
		idx := int(math.Ceil(float64(len(sorted))*0.99)) - 1
		if idx >= 0 && idx < len(sorted) {
			m.P99LatencyMs = sorted[idx]
		}
	}

	return m
}

// DroneCount 등록 드론 수
func (b *CommBroker) DroneCount() int {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return len(b.drones)
}

// ConnectedDrones 연결된 드론 ID 목록
func (b *CommBroker) ConnectedDrones() []string {
	b.mu.RLock()
	defer b.mu.RUnlock()

	ids := make([]string, 0)
	for _, d := range b.drones {
		if d.Connected {
			ids = append(ids, d.DroneID)
		}
	}
	return ids
}
