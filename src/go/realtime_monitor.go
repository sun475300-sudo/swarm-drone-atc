// Phase 651 — Go Realtime Monitor (goroutine-based parallel telemetry collection)
package main

import (
	"fmt"
	"sync"
	"time"
)

type TelemetryFrame struct {
	DroneID   string
	X, Y, Z   float64
	Timestamp time.Time
}

type RealtimeMonitor struct {
	mu      sync.RWMutex
	drones  map[string]TelemetryFrame
	updates chan TelemetryFrame
}

func NewRealtimeMonitor() *RealtimeMonitor {
	m := &RealtimeMonitor{
		drones:  make(map[string]TelemetryFrame),
		updates: make(chan TelemetryFrame, 100),
	}
	go m.processUpdates()
	return m
}

func (m *RealtimeMonitor) Publish(frame TelemetryFrame) {
	m.updates <- frame
}

func (m *RealtimeMonitor) processUpdates() {
	for frame := range m.updates {
		m.mu.Lock()
		m.drones[frame.DroneID] = frame
		m.mu.Unlock()
	}
}

func (m *RealtimeMonitor) Snapshot() map[string]TelemetryFrame {
	m.mu.RLock()
	defer m.mu.RUnlock()
	result := make(map[string]TelemetryFrame, len(m.drones))
	for k, v := range m.drones {
		result[k] = v
	}
	return result
}

func main() {
	monitor := NewRealtimeMonitor()
	monitor.Publish(TelemetryFrame{DroneID: "D1", X: 0, Y: 0, Z: 50, Timestamp: time.Now()})
	time.Sleep(10 * time.Millisecond)
	fmt.Printf("Active drones: %d\n", len(monitor.Snapshot()))
}
