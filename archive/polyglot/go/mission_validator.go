// Phase 493: Mission Critical Validator (Go)
// 미션 사전검증, 안전 제약 체크, Go 채널 기반 실시간 모니터링

package mission_validator

import (
	"fmt"
	"math"
	"sync"
	"time"
)

type ValidationLevel int

const (
	Info ValidationLevel = iota
	Warning
	Critical
	Blocker
)

func (v ValidationLevel) String() string {
	return [...]string{"INFO", "WARNING", "CRITICAL", "BLOCKER"}[v]
}

type CheckCategory string

const (
	CatBattery   CheckCategory = "battery"
	CatWeather   CheckCategory = "weather"
	CatAirspace  CheckCategory = "airspace"
	CatGeofence  CheckCategory = "geofence"
	CatHardware  CheckCategory = "hardware"
	CatComm      CheckCategory = "communication"
)

type ValidationResult struct {
	CheckID   string
	Category  CheckCategory
	Level     ValidationLevel
	Message   string
	Passed    bool
	Value     float64
	Threshold float64
}

type Waypoint struct {
	X, Y, Z float64
}

func (w Waypoint) DistanceTo(other Waypoint) float64 {
	dx := w.X - other.X
	dy := w.Y - other.Y
	dz := w.Z - other.Z
	return math.Sqrt(dx*dx + dy*dy + dz*dz)
}

type MissionPlan struct {
	MissionID   string
	DroneIDs    []string
	Waypoints   []Waypoint
	MaxAltitude float64
	DurationMin float64
	PayloadKg   float64
}

type SafetyEnvelope struct {
	MinAltitude     float64
	MaxAltitude     float64
	MaxSpeed        float64
	MinBattery      float64
	MaxWind         float64
	MaxDistance      float64
	MinSignalDBM    float64
}

func DefaultEnvelope() SafetyEnvelope {
	return SafetyEnvelope{
		MinAltitude:  5,
		MaxAltitude:  150,
		MaxSpeed:     20,
		MinBattery:   20,
		MaxWind:      12,
		MaxDistance:   5000,
		MinSignalDBM: -80,
	}
}

type MissionValidator struct {
	mu          sync.RWMutex
	envelope    SafetyEnvelope
	results     []ValidationResult
	checkCount  int
}

func NewValidator(envelope SafetyEnvelope) *MissionValidator {
	return &MissionValidator{
		envelope: envelope,
		results:  make([]ValidationResult, 0, 32),
	}
}

func (v *MissionValidator) addResult(cat CheckCategory, level ValidationLevel,
	msg string, passed bool, value, threshold float64) ValidationResult {
	v.checkCount++
	r := ValidationResult{
		CheckID:   fmt.Sprintf("CHK-%04d", v.checkCount),
		Category:  cat,
		Level:     level,
		Message:   msg,
		Passed:    passed,
		Value:     value,
		Threshold: threshold,
	}
	v.results = append(v.results, r)
	return r
}

func (v *MissionValidator) ValidateBattery(batteryPct, flightTimeMin float64) []ValidationResult {
	v.mu.Lock()
	defer v.mu.Unlock()
	var results []ValidationResult
	required := flightTimeMin*1.5 + v.envelope.MinBattery
	r := v.addResult(CatBattery, Critical,
		fmt.Sprintf("Battery %.0f%% vs required %.0f%%", batteryPct, required),
		batteryPct >= required, batteryPct, required)
	results = append(results, r)
	if batteryPct < 50 {
		r = v.addResult(CatBattery, Warning,
			fmt.Sprintf("Battery below 50%%: %.0f%%", batteryPct),
			false, batteryPct, 50)
		results = append(results, r)
	}
	return results
}

func (v *MissionValidator) ValidateWeather(windSpeed, visibility float64) []ValidationResult {
	v.mu.Lock()
	defer v.mu.Unlock()
	var results []ValidationResult
	results = append(results, v.addResult(CatWeather, Critical,
		fmt.Sprintf("Wind %.1f m/s vs limit %.1f", windSpeed, v.envelope.MaxWind),
		windSpeed <= v.envelope.MaxWind, windSpeed, v.envelope.MaxWind))
	results = append(results, v.addResult(CatWeather, Warning,
		fmt.Sprintf("Visibility %.0fm", visibility),
		visibility >= 1000, visibility, 1000))
	return results
}

func (v *MissionValidator) ValidateAirspace(waypoints []Waypoint) []ValidationResult {
	v.mu.Lock()
	defer v.mu.Unlock()
	var results []ValidationResult
	for i, wp := range waypoints {
		if wp.Z > v.envelope.MaxAltitude {
			results = append(results, v.addResult(CatAirspace, Blocker,
				fmt.Sprintf("WP%d altitude %.0fm exceeds %.0fm", i, wp.Z, v.envelope.MaxAltitude),
				false, wp.Z, v.envelope.MaxAltitude))
		}
		if wp.Z < v.envelope.MinAltitude {
			results = append(results, v.addResult(CatAirspace, Critical,
				fmt.Sprintf("WP%d altitude %.0fm below min %.0fm", i, wp.Z, v.envelope.MinAltitude),
				false, wp.Z, v.envelope.MinAltitude))
		}
	}
	if len(results) == 0 {
		results = append(results, v.addResult(CatAirspace, Info,
			"All waypoints within safe airspace", true, 0, 0))
	}
	return results
}

func (v *MissionValidator) ValidateMission(plan MissionPlan, batteryPct, windSpeed float64) map[string]interface{} {
	v.mu.Lock()
	v.results = v.results[:0]
	v.checkCount = 0
	v.mu.Unlock()

	var wg sync.WaitGroup
	wg.Add(3)
	go func() { defer wg.Done(); v.ValidateBattery(batteryPct, plan.DurationMin) }()
	go func() { defer wg.Done(); v.ValidateWeather(windSpeed, 5000) }()
	go func() { defer wg.Done(); v.ValidateAirspace(plan.Waypoints) }()
	wg.Wait()

	// Distance check
	v.mu.Lock()
	totalDist := 0.0
	for i := 1; i < len(plan.Waypoints); i++ {
		totalDist += plan.Waypoints[i].DistanceTo(plan.Waypoints[i-1])
	}
	if totalDist > v.envelope.MaxDistance {
		v.addResult(CatGeofence, Critical,
			fmt.Sprintf("Total distance %.0fm exceeds %.0fm", totalDist, v.envelope.MaxDistance),
			false, totalDist, v.envelope.MaxDistance)
	}

	blockers := 0
	criticals := 0
	passed := 0
	for _, r := range v.results {
		if r.Passed {
			passed++
		}
		if !r.Passed && r.Level == Blocker {
			blockers++
		}
		if !r.Passed && r.Level == Critical {
			criticals++
		}
	}
	v.mu.Unlock()

	goNoGo := "GO"
	if blockers > 0 || criticals > 0 {
		goNoGo = "NO-GO"
	}

	return map[string]interface{}{
		"mission_id":  plan.MissionID,
		"go_no_go":    goNoGo,
		"total_checks": len(v.results),
		"passed":      passed,
		"blockers":    blockers,
		"criticals":   criticals,
		"validated_at": time.Now().Unix(),
	}
}
