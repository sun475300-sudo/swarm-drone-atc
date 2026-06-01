// Phase 641: Realtime Swarm Monitor — 실시간 드론 상태 모니터링
package main

import (
	"fmt"
	"math"
	"math/rand"
	"time"
)

// DroneStatus holds live telemetry for a single drone.
type DroneStatus struct {
	ID       int
	X, Y, Z  float64
	Battery  float64 // 0-100 %
	Velocity float64 // m/s
	Alive    bool
}

// Alert encodes a monitoring alert.
type Alert struct {
	DroneID  int
	Severity string // INFO, WARN, CRITICAL
	Message  string
	Time     time.Time
}

// RealtimeMonitor tracks fleet health in real time.
type RealtimeMonitor struct {
	Drones  []*DroneStatus
	Alerts  []Alert
	Tick    int
	rng     *rand.Rand
}

// NewRealtimeMonitor creates a monitor for n drones.
func NewRealtimeMonitor(n int, seed int64) *RealtimeMonitor {
	drones := make([]*DroneStatus, n)
	r := rand.New(rand.NewSource(seed))
	for i := range drones {
		drones[i] = &DroneStatus{
			ID:      i,
			X:       r.Float64() * 500,
			Y:       r.Float64() * 500,
			Z:       r.Float64() * 120,
			Battery: 80 + r.Float64()*20,
			Alive:   true,
		}
	}
	return &RealtimeMonitor{Drones: drones, rng: r}
}

// Step advances simulation by one tick and fires alerts.
func (m *RealtimeMonitor) Step() {
	m.Tick++
	for _, d := range m.Drones {
		if !d.Alive {
			continue
		}
		// Simulate battery drain
		d.Battery -= 0.05 + m.rng.Float64()*0.1
		d.Velocity = 5 + m.rng.Float64()*10

		// Position update
		d.X += (m.rng.Float64() - 0.5) * 2
		d.Y += (m.rng.Float64() - 0.5) * 2
		d.Z = math.Max(10, d.Z+(m.rng.Float64()-0.5)*1)

		// Alert rules
		if d.Battery < 20 {
			m.Alerts = append(m.Alerts, Alert{
				DroneID:  d.ID,
				Severity: "CRITICAL",
				Message:  fmt.Sprintf("Low battery: %.1f%%", d.Battery),
				Time:     time.Now(),
			})
		} else if d.Battery < 40 {
			m.Alerts = append(m.Alerts, Alert{
				DroneID:  d.ID,
				Severity: "WARN",
				Message:  fmt.Sprintf("Battery warning: %.1f%%", d.Battery),
				Time:     time.Now(),
			})
		}
		if d.Battery <= 0 {
			d.Alive = false
		}
	}
}

// Run executes n ticks.
func (m *RealtimeMonitor) Run(ticks int) {
	for i := 0; i < ticks; i++ {
		m.Step()
	}
}

// AliveDrones returns count of active drones.
func (m *RealtimeMonitor) AliveDrones() int {
	count := 0
	for _, d := range m.Drones {
		if d.Alive {
			count++
		}
	}
	return count
}

func main() {
	fmt.Println("Phase 641: Realtime Monitor — 실시간 군집 드론 감시")
	mon := NewRealtimeMonitor(10, 42)
	mon.Run(100)
	fmt.Printf("Alive: %d, Alerts: %d\n", mon.AliveDrones(), len(mon.Alerts))
}
