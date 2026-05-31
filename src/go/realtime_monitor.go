// Realtime Monitor — SDACS Phase 651
package monitor

import (
	"sync"
	"time"
)

type DroneState struct {
	ID      string
	Lat     float64
	Lon     float64
	Alt     float64
	Updated time.Time
}

type Monitor struct {
	mu     sync.RWMutex
	drones map[string]*DroneState
}

func NewMonitor() *Monitor {
	return &Monitor{drones: make(map[string]*DroneState)}
}

func (m *Monitor) Update(d *DroneState) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.drones[d.ID] = d
}
