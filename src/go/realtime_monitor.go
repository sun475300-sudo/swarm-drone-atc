// P651: Real-time Monitor - Go stub
// WebSocket-based real-time drone monitoring service

package realtime

import (
	"encoding/json"
	"sync"
	"time"
)

type DroneMetrics struct {
	DroneID   string    `json:"drone_id"`
	Timestamp time.Time `json:"timestamp"`
	Position  [3]float64 `json:"position"`
	Velocity  [3]float64 `json:"velocity"`
	Battery   float64   `json:"battery"`
	Status    string    `json:"status"`
}

type Monitor struct {
	mu      sync.RWMutex
	drones  map[string]*DroneMetrics
	updates chan *DroneMetrics
}

func NewMonitor() *Monitor {
	return &Monitor{
		drones:  make(map[string]*DroneMetrics),
		updates: make(chan *DroneMetrics, 100),
	}
}

func (m *Monitor) Update(metrics *DroneMetrics) {
	m.mu.Lock()
	m.drones[metrics.DroneID] = metrics
	m.mu.Unlock()

	select {
	case m.updates <- metrics:
	default:
	}
}

func (m *Monitor) GetAll() []*DroneMetrics {
	m.mu.RLock()
	defer m.mu.RUnlock()
	result := make([]*DroneMetrics, 0, len(m.drones))
	for _, d := range m.drones {
		result = append(result, d)
	}
	return result
}

func (m *Monitor) ToJSON() ([]byte, error) {
	return json.Marshal(m.GetAll())
}

func (m *Monitor) Updates() <-chan *DroneMetrics {
	return m.updates
}
