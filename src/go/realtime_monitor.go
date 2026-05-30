// SDACS Realtime Monitor — Go
// 드론 군집 실시간 상태 모니터링

package monitor

import (
	"fmt"
	"math"
	"sort"
	"sync"
	"time"
)

// DroneMetrics represents a single telemetry snapshot.
type DroneMetrics struct {
	ID        string
	X, Y, Z   float64
	VX, VY, VZ float64
	Battery   float64
	State     string
	Timestamp time.Time
}

// ConflictEvent records a proximity conflict between two drones.
type ConflictEvent struct {
	DroneA    string
	DroneB    string
	Distance  float64
	Severity  string
	At        time.Time
}

// FleetMonitor aggregates metrics across the whole fleet.
type FleetMonitor struct {
	mu        sync.RWMutex
	fleet     map[string]*DroneMetrics
	conflicts []ConflictEvent
	threshold float64
	startTime time.Time
}

// NewFleetMonitor creates a new monitor with the given separation threshold.
func NewFleetMonitor(threshold float64) *FleetMonitor {
	return &FleetMonitor{
		fleet:     make(map[string]*DroneMetrics),
		threshold: threshold,
		startTime: time.Now(),
	}
}

// Update ingests a new telemetry frame.
func (m *FleetMonitor) Update(metrics DroneMetrics) {
	m.mu.Lock()
	defer m.mu.Unlock()
	metrics.Timestamp = time.Now()
	m.fleet[metrics.ID] = &metrics
}

// DetectConflicts scans all pairs and returns new conflict events.
func (m *FleetMonitor) DetectConflicts() []ConflictEvent {
	m.mu.Lock()
	defer m.mu.Unlock()

	drones := make([]*DroneMetrics, 0, len(m.fleet))
	for _, d := range m.fleet {
		drones = append(drones, d)
	}

	var events []ConflictEvent
	for i := 0; i < len(drones); i++ {
		for j := i + 1; j < len(drones); j++ {
			a, b := drones[i], drones[j]
			dist := distance3D(a, b)
			if dist < m.threshold {
				sev := severity(dist, m.threshold)
				ev := ConflictEvent{
					DroneA:   a.ID,
					DroneB:   b.ID,
					Distance: dist,
					Severity: sev,
					At:       time.Now(),
				}
				events = append(events, ev)
				m.conflicts = append(m.conflicts, ev)
			}
		}
	}
	return events
}

// Summary returns fleet-wide statistics.
func (m *FleetMonitor) Summary() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var batSum, altSum float64
	low := 0
	for _, d := range m.fleet {
		batSum += d.Battery
		altSum += d.Z
		if d.Battery < 20.0 {
			low++
		}
	}
	n := float64(len(m.fleet))
	if n == 0 {
		n = 1
	}
	return map[string]interface{}{
		"total_drones":     len(m.fleet),
		"low_battery":      low,
		"avg_battery":      batSum / n,
		"avg_altitude":     altSum / n,
		"total_conflicts":  len(m.conflicts),
		"uptime_seconds":   time.Since(m.startTime).Seconds(),
	}
}

// LowBatteryDrones returns IDs of drones below 20% battery.
func (m *FleetMonitor) LowBatteryDrones() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	var ids []string
	for id, d := range m.fleet {
		if d.Battery < 20.0 {
			ids = append(ids, id)
		}
	}
	sort.Strings(ids)
	return ids
}

// Report generates a human-readable report.
func (m *FleetMonitor) Report() string {
	s := m.Summary()
	return fmt.Sprintf(
		"=== SDACS Fleet Monitor ===\nDrones: %v | Low Battery: %v | Conflicts: %v\n"+
			"Avg Battery: %.1f%% | Avg Altitude: %.1fm | Uptime: %.1fs",
		s["total_drones"], s["low_battery"], s["total_conflicts"],
		s["avg_battery"], s["avg_altitude"], s["uptime_seconds"],
	)
}

func distance3D(a, b *DroneMetrics) float64 {
	dx := a.X - b.X
	dy := a.Y - b.Y
	dz := a.Z - b.Z
	return math.Sqrt(dx*dx + dy*dy + dz*dz)
}

func severity(dist, threshold float64) string {
	ratio := dist / threshold
	switch {
	case ratio < 0.3:
		return "CRITICAL"
	case ratio < 0.6:
		return "HIGH"
	default:
		return "MEDIUM"
	}
}
