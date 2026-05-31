// Phase 651 — Real-time Monitor (Go)
// 군집 드론 실시간 상태 모니터링 서비스

package monitor

import (
	"encoding/json"
	"fmt"
	"math"
	"sync"
	"time"
)

// DroneState는 드론 한 대의 텔레메트리 스냅샷이다.
type DroneState struct {
	ID         string     `json:"id"`
	Position   [3]float64 `json:"pos"`
	Velocity   [3]float64 `json:"vel"`
	Phase      string     `json:"phase"`
	BatteryPct float64    `json:"battery"`
	UpdatedAt  time.Time  `json:"updated_at"`
}

// Speed는 드론의 현재 속력(스칼라)을 반환한다.
func (d *DroneState) Speed() float64 {
	v := d.Velocity
	return math.Sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
}

// Monitor는 전체 군집의 실시간 상태를 관리한다.
type Monitor struct {
	mu     sync.RWMutex
	drones map[string]*DroneState
	alerts []string
}

// NewMonitor는 빈 Monitor를 생성한다.
func NewMonitor() *Monitor {
	return &Monitor{drones: make(map[string]*DroneState)}
}

// Update는 드론 상태를 갱신한다.
func (m *Monitor) Update(state DroneState) {
	state.UpdatedAt = time.Now()
	m.mu.Lock()
	defer m.mu.Unlock()
	m.drones[state.ID] = &state
	if state.BatteryPct < 20.0 {
		m.alerts = append(m.alerts, fmt.Sprintf("LOW_BATTERY:%s:%.1f%%", state.ID, state.BatteryPct))
	}
}

// Snapshot은 전체 드론 상태의 JSON 스냅샷을 반환한다.
func (m *Monitor) Snapshot() ([]byte, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	states := make([]*DroneState, 0, len(m.drones))
	for _, s := range m.drones {
		states = append(states, s)
	}
	return json.Marshal(map[string]any{
		"count":  len(states),
		"drones": states,
		"alerts": m.alerts,
	})
}

// ActiveCount는 CRUISE 또는 APPROACH 단계에 있는 드론 수를 반환한다.
func (m *Monitor) ActiveCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	count := 0
	for _, s := range m.drones {
		if s.Phase == "CRUISE" || s.Phase == "APPROACH" {
			count++
		}
	}
	return count
}
