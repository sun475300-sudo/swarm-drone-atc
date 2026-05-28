// Phase 651: Realtime Monitor — Go Concurrent Fleet Monitor
// 실시간 군집 모니터: goroutine 기반 병렬 드론 상태 수집 및 이상 탐지

package main

import (
	"fmt"
	"math"
	"math/rand"
	"sync"
	"time"
)

// DroneStatus represents a single drone's telemetry snapshot
type DroneStatus struct {
	DroneID    string
	Position   [3]float64
	Velocity   [3]float64
	BatteryPct float64
	IsActive   bool
	Timestamp  time.Time
}

// Alert represents a fleet monitoring alert
type Alert struct {
	Level   string // "info", "warning", "critical"
	DroneID string
	Message string
	Time    time.Time
}

// FleetMonitor manages concurrent drone status collection
type FleetMonitor struct {
	mu       sync.RWMutex
	drones   map[string]*DroneStatus
	alerts   []Alert
	interval time.Duration
}

// NewFleetMonitor creates a new FleetMonitor instance
func NewFleetMonitor(intervalMs int) *FleetMonitor {
	return &FleetMonitor{
		drones:   make(map[string]*DroneStatus),
		alerts:   make([]Alert, 0),
		interval: time.Duration(intervalMs) * time.Millisecond,
	}
}

// UpdateDrone updates a drone's status thread-safely
func (fm *FleetMonitor) UpdateDrone(status DroneStatus) {
	fm.mu.Lock()
	defer fm.mu.Unlock()
	fm.drones[status.DroneID] = &status

	// Check for anomalies
	if status.BatteryPct < 20.0 {
		fm.alerts = append(fm.alerts, Alert{
			Level:   "warning",
			DroneID: status.DroneID,
			Message: fmt.Sprintf("Low battery: %.1f%%", status.BatteryPct),
			Time:    time.Now(),
		})
	}

	speed := math.Sqrt(
		status.Velocity[0]*status.Velocity[0] +
			status.Velocity[1]*status.Velocity[1] +
			status.Velocity[2]*status.Velocity[2])
	if speed > 30.0 {
		fm.alerts = append(fm.alerts, Alert{
			Level:   "critical",
			DroneID: status.DroneID,
			Message: fmt.Sprintf("Excessive speed: %.1f m/s", speed),
			Time:    time.Now(),
		})
	}
}

// GetDrone returns a drone's status
func (fm *FleetMonitor) GetDrone(droneID string) (*DroneStatus, bool) {
	fm.mu.RLock()
	defer fm.mu.RUnlock()
	d, ok := fm.drones[droneID]
	return d, ok
}

// FleetSummary returns aggregated fleet statistics
func (fm *FleetMonitor) FleetSummary() map[string]interface{} {
	fm.mu.RLock()
	defer fm.mu.RUnlock()

	active := 0
	var totalBat float64
	for _, d := range fm.drones {
		if d.IsActive {
			active++
		}
		totalBat += d.BatteryPct
	}

	return map[string]interface{}{
		"total_drones":  len(fm.drones),
		"active_drones": active,
		"avg_battery":   totalBat / math.Max(float64(len(fm.drones)), 1),
		"alert_count":   len(fm.alerts),
	}
}

// SimulateFleet runs a concurrent fleet simulation
func (fm *FleetMonitor) SimulateFleet(nDrones int, nTicks int) {
	rng := rand.New(rand.NewSource(42))
	var wg sync.WaitGroup

	for i := 0; i < nDrones; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			droneID := fmt.Sprintf("D-%04d", id)
			pos := [3]float64{
				rng.Float64()*4000 - 2000,
				rng.Float64()*4000 - 2000,
				30 + rng.Float64()*90,
			}
			vel := [3]float64{
				rng.Float64()*10 - 5,
				rng.Float64()*10 - 5,
				rng.Float64()*2 - 1,
			}
			bat := 80.0 + rng.Float64()*20.0

			for t := 0; t < nTicks; t++ {
				pos[0] += vel[0] * 0.1
				pos[1] += vel[1] * 0.1
				pos[2] += vel[2] * 0.1
				bat -= 0.05

				fm.UpdateDrone(DroneStatus{
					DroneID:    droneID,
					Position:   pos,
					Velocity:   vel,
					BatteryPct: math.Max(bat, 0),
					IsActive:   bat > 5.0,
					Timestamp:  time.Now(),
				})
			}
		}(i)
	}
	wg.Wait()
}

func main() {
	monitor := NewFleetMonitor(100)
	monitor.SimulateFleet(50, 100)
	summary := monitor.FleetSummary()
	for k, v := range summary {
		fmt.Printf("  %s: %v\n", k, v)
	}
}
