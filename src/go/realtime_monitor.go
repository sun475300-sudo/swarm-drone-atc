// Phase 651 — Realtime Swarm Monitor in Go (goroutine-based)
package monitor

import (
	"context"
	"sync"
	"time"
)

type DroneState struct {
	ID  string
	X, Y, Z float64
	VX, VY, VZ float64
	Timestamp   time.Time
}

type Monitor struct {
	mu     sync.RWMutex
	states map[string]DroneState
}

func New() *Monitor { return &Monitor{states: make(map[string]DroneState)} }

func (m *Monitor) Update(s DroneState) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.states[s.ID] = s
}

func (m *Monitor) Snapshot() []DroneState {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make([]DroneState, 0, len(m.states))
	for _, s := range m.states { out = append(out, s) }
	return out
}

func (m *Monitor) Run(ctx context.Context, interval time.Duration, fn func([]DroneState)) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done(): return
		case <-ticker.C: fn(m.Snapshot())
		}
	}
}
