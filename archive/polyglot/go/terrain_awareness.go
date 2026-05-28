// Phase 309: Go Terrain Awareness System
// Procedural DEM generation, TAWS alerts, MSA calculation.
// Goroutine-safe with read-write mutex for concurrent access.

package terrain

import (
	"fmt"
	"math"
	"sync"
)

// Vec3 represents a 3D position
type Vec3 struct {
	X, Y, Z float64
}

func (a Vec3) Sub(b Vec3) Vec3 {
	return Vec3{a.X - b.X, a.Y - b.Y, a.Z - b.Z}
}

func (v Vec3) Length() float64 {
	return math.Sqrt(v.X*v.X + v.Y*v.Y + v.Z*v.Z)
}

// AlertLevel represents TAWS alert severity
type AlertLevel int

const (
	AlertNone AlertLevel = iota
	AlertCaution
	AlertWarning
	AlertPullUp
)

func (a AlertLevel) String() string {
	switch a {
	case AlertCaution:
		return "CAUTION"
	case AlertWarning:
		return "WARNING"
	case AlertPullUp:
		return "PULL_UP"
	default:
		return "NONE"
	}
}

// TAWSAlert represents a terrain awareness alert
type TAWSAlert struct {
	DroneID      string
	Level        AlertLevel
	TerrainAlt   float64
	DroneAlt     float64
	Clearance    float64
	Message      string
}

// TerrainCell represents a DEM grid cell
type TerrainCell struct {
	Elevation float64
	Type      string // "flat", "hill", "mountain", "water"
}

// TerrainAwarenessSystem provides terrain awareness and alerting
type TerrainAwarenessSystem struct {
	mu          sync.RWMutex
	grid        [][]TerrainCell
	gridSizeX   int
	gridSizeY   int
	cellSize    float64
	originX     float64
	originY     float64
	minSafeAlt  float64 // MSA in meters AGL
	alerts      []TAWSAlert
	alertCount  int
}

// NewTerrainAwarenessSystem creates a new TAS with procedural terrain
func NewTerrainAwarenessSystem(sizeX, sizeY int, cellSize float64) *TerrainAwarenessSystem {
	tas := &TerrainAwarenessSystem{
		gridSizeX:  sizeX,
		gridSizeY:  sizeY,
		cellSize:   cellSize,
		originX:    0,
		originY:    0,
		minSafeAlt: 30.0,
		alerts:     make([]TAWSAlert, 0, 100),
	}
	tas.generateTerrain()
	return tas
}

// generateTerrain creates procedural terrain using sine-based heightmap
func (tas *TerrainAwarenessSystem) generateTerrain() {
	tas.grid = make([][]TerrainCell, tas.gridSizeX)
	for i := 0; i < tas.gridSizeX; i++ {
		tas.grid[i] = make([]TerrainCell, tas.gridSizeY)
		for j := 0; j < tas.gridSizeY; j++ {
			x := float64(i) * tas.cellSize
			y := float64(j) * tas.cellSize

			// Multi-octave noise approximation
			elev := 20.0 * math.Sin(x*0.01) * math.Cos(y*0.01)
			elev += 10.0 * math.Sin(x*0.03+1.0) * math.Sin(y*0.02+2.0)
			elev += 5.0 * math.Cos(x*0.05) * math.Sin(y*0.04)
			elev = math.Max(0, elev)

			cellType := "flat"
			if elev > 25.0 {
				cellType = "mountain"
			} else if elev > 10.0 {
				cellType = "hill"
			} else if elev < 1.0 {
				cellType = "water"
			}

			tas.grid[i][j] = TerrainCell{
				Elevation: elev,
				Type:      cellType,
			}
		}
	}
}

// GetElevation returns terrain elevation at given world coordinates
func (tas *TerrainAwarenessSystem) GetElevation(x, y float64) float64 {
	tas.mu.RLock()
	defer tas.mu.RUnlock()

	ix := int((x - tas.originX) / tas.cellSize)
	iy := int((y - tas.originY) / tas.cellSize)

	if ix < 0 || ix >= tas.gridSizeX || iy < 0 || iy >= tas.gridSizeY {
		return 0.0
	}
	return tas.grid[ix][iy].Elevation
}

// CheckTerrain evaluates TAWS alert for a drone position
func (tas *TerrainAwarenessSystem) CheckTerrain(droneID string, pos Vec3) TAWSAlert {
	terrainAlt := tas.GetElevation(pos.X, pos.Y)
	clearance := pos.Z - terrainAlt

	alert := TAWSAlert{
		DroneID:    droneID,
		Level:      AlertNone,
		TerrainAlt: terrainAlt,
		DroneAlt:   pos.Z,
		Clearance:  clearance,
	}

	if clearance < tas.minSafeAlt*0.3 {
		alert.Level = AlertPullUp
		alert.Message = fmt.Sprintf("PULL UP! Clearance %.1fm", clearance)
	} else if clearance < tas.minSafeAlt*0.6 {
		alert.Level = AlertWarning
		alert.Message = fmt.Sprintf("TERRAIN WARNING: Clearance %.1fm", clearance)
	} else if clearance < tas.minSafeAlt {
		alert.Level = AlertCaution
		alert.Message = fmt.Sprintf("TERRAIN CAUTION: Clearance %.1fm", clearance)
	}

	if alert.Level != AlertNone {
		tas.mu.Lock()
		tas.alerts = append(tas.alerts, alert)
		tas.alertCount++
		tas.mu.Unlock()
	}

	return alert
}

// ValidatePath checks an entire path for terrain conflicts
func (tas *TerrainAwarenessSystem) ValidatePath(droneID string, path []Vec3) []TAWSAlert {
	var alerts []TAWSAlert
	for _, pos := range path {
		alert := tas.CheckTerrain(droneID, pos)
		if alert.Level != AlertNone {
			alerts = append(alerts, alert)
		}
	}
	return alerts
}

// GetMSA returns Minimum Safe Altitude in an area
func (tas *TerrainAwarenessSystem) GetMSA(centerX, centerY, radius float64) float64 {
	tas.mu.RLock()
	defer tas.mu.RUnlock()

	maxElev := 0.0
	ixMin := int(math.Max(0, (centerX-radius-tas.originX)/tas.cellSize))
	ixMax := int(math.Min(float64(tas.gridSizeX-1), (centerX+radius-tas.originX)/tas.cellSize))
	iyMin := int(math.Max(0, (centerY-radius-tas.originY)/tas.cellSize))
	iyMax := int(math.Min(float64(tas.gridSizeY-1), (centerY+radius-tas.originY)/tas.cellSize))

	for ix := ixMin; ix <= ixMax; ix++ {
		for iy := iyMin; iy <= iyMax; iy++ {
			if tas.grid[ix][iy].Elevation > maxElev {
				maxElev = tas.grid[ix][iy].Elevation
			}
		}
	}

	return maxElev + tas.minSafeAlt
}

// GetAlerts returns recent alerts
func (tas *TerrainAwarenessSystem) GetAlerts(limit int) []TAWSAlert {
	tas.mu.RLock()
	defer tas.mu.RUnlock()

	if len(tas.alerts) <= limit {
		result := make([]TAWSAlert, len(tas.alerts))
		copy(result, tas.alerts)
		return result
	}
	start := len(tas.alerts) - limit
	result := make([]TAWSAlert, limit)
	copy(result, tas.alerts[start:])
	return result
}

// Summary returns terrain system statistics
func (tas *TerrainAwarenessSystem) Summary() map[string]interface{} {
	tas.mu.RLock()
	defer tas.mu.RUnlock()

	typeCounts := make(map[string]int)
	for i := 0; i < tas.gridSizeX; i++ {
		for j := 0; j < tas.gridSizeY; j++ {
			typeCounts[tas.grid[i][j].Type]++
		}
	}

	return map[string]interface{}{
		"grid_size":    fmt.Sprintf("%dx%d", tas.gridSizeX, tas.gridSizeY),
		"cell_size_m":  tas.cellSize,
		"msa_m":        tas.minSafeAlt,
		"terrain_types": typeCounts,
		"total_alerts":  tas.alertCount,
	}
}
