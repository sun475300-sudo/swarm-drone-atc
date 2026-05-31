// realtime_monitor.go - Real-time drone swarm monitor for SDACS
package monitor

import (
	"fmt"
	"math"
	"sync"
	"time"
)

type DroneState struct {
	ID        string
	X, Y, Z   float64
	Vx, Vy, Vz float64
	Battery   int
	Status    string
	UpdatedAt time.Time
}

type Monitor struct {
	mu     sync.RWMutex
	drones map[string]*DroneState
}

func NewMonitor() *Monitor {
	return &Monitor{drones: make(map[string]*DroneState)}
}

func (m *Monitor) UpdateDrone(state *DroneState) {
	m.mu.Lock()
	defer m.mu.Unlock()
	state.UpdatedAt = time.Now()
	m.drones[state.ID] = state
}

func (m *Monitor) GetDrone(id string) (*DroneState, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	d, ok := m.drones[id]
	return d, ok
}

func (m *Monitor) GetConflicts(minSep float64) [][2]string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	var conflicts [][2]string
	ids := make([]string, 0, len(m.drones))
	for id := range m.drones { ids = append(ids, id) }
	for i := 0; i < len(ids); i++ {
		for j := i + 1; j < len(ids); j++ {
			a, b := m.drones[ids[i]], m.drones[ids[j]]
			dx, dy, dz := a.X-b.X, a.Y-b.Y, a.Z-b.Z
			if math.Sqrt(dx*dx+dy*dy+dz*dz) < minSep {
				conflicts = append(conflicts, [2]string{ids[i], ids[j]})
			}
		}
	}
	return conflicts
}

func (m *Monitor) Summary() string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return fmt.Sprintf("Monitor: %d drones tracked", len(m.drones))
}
