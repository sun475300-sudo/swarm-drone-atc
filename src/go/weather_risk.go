// Package weatherrisk provides weather-aware risk scoring for SDACS.
package weatherrisk

import "math"

type Input struct {
	WindMps            float64
	VisibilityKm       float64
	PrecipitationLevel float64
	Congestion         float64
}

type Output struct {
	Score    float64
	Category string
}

func clamp(v, lo, hi float64) float64 {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

func Compute(input Input) Output {
	windNorm := clamp(input.WindMps/20.0, 0.0, 1.0)
	visNorm := clamp(input.VisibilityKm/10.0, 0.0, 1.0)
	visPenalty := 1.0 - visNorm
	precip := clamp(input.PrecipitationLevel, 0.0, 1.0)
	congestion := clamp(input.Congestion, 0.0, 1.0)

	raw := 0.35*windNorm + 0.25*visPenalty + 0.20*precip + 0.20*congestion
	score := math.Round(clamp(raw, 0.0, 1.0)*10000.0) / 10000.0

	category := "RED"
	if score < 0.25 {
		category = "GREEN"
	} else if score < 0.50 {
		category = "YELLOW"
	} else if score < 0.75 {
		category = "ORANGE"
	}

	return Output{Score: score, Category: category}
}
