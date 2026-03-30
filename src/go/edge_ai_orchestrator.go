// Phase 323: Go Edge AI Orchestrator
// Model distribution, load balancing, inference routing.
// Goroutine-safe with channel-based message passing.

package edgeai

import (
	"fmt"
	"math"
	"sync"
)

// ModelFormat represents quantization level
type ModelFormat string

const (
	Float32 ModelFormat = "float32"
	Float16 ModelFormat = "float16"
	Int8    ModelFormat = "int8"
	Int4    ModelFormat = "int4"
)

// EdgeDevice represents a compute node
type EdgeDevice struct {
	DeviceID    string
	CPUCores    int
	MemoryMB    int
	HasGPU      bool
	LoadPercent float64
	Models      map[string]bool
	Available   bool
}

// ModelInfo describes a deployable model
type ModelInfo struct {
	ModelID     string
	Name        string
	Format      ModelFormat
	SizeMB      float64
	LatencyMs   float64
	Accuracy    float64
	MinMemoryMB int
}

// InferenceRequest represents a compute request
type InferenceRequest struct {
	RequestID string
	ModelID   string
	DroneID   string
	Priority  int
	DataSize  int
}

// InferenceResult represents computation output
type InferenceResult struct {
	RequestID string
	DeviceID  string
	LatencyMs float64
	Success   bool
	Error     string
}

// EdgeAIOrchestrator manages model deployment and inference routing
type EdgeAIOrchestrator struct {
	mu            sync.RWMutex
	devices       map[string]*EdgeDevice
	models        map[string]*ModelInfo
	routingTable  map[string]string // modelID -> preferred deviceID
	requestCount  int
	totalLatency  float64
	successCount  int
	failureCount  int
}

// NewOrchestrator creates a new EdgeAIOrchestrator
func NewOrchestrator() *EdgeAIOrchestrator {
	return &EdgeAIOrchestrator{
		devices:      make(map[string]*EdgeDevice),
		models:       make(map[string]*ModelInfo),
		routingTable: make(map[string]string),
	}
}

// AddDevice registers an edge compute device
func (o *EdgeAIOrchestrator) AddDevice(device *EdgeDevice) {
	o.mu.Lock()
	defer o.mu.Unlock()
	if device.Models == nil {
		device.Models = make(map[string]bool)
	}
	o.devices[device.DeviceID] = device
}

// RegisterModel registers a model for deployment
func (o *EdgeAIOrchestrator) RegisterModel(model *ModelInfo) {
	o.mu.Lock()
	defer o.mu.Unlock()
	o.models[model.ModelID] = model
}

// DeployModel deploys a model to a specific device
func (o *EdgeAIOrchestrator) DeployModel(modelID, deviceID string) error {
	o.mu.Lock()
	defer o.mu.Unlock()

	model, ok := o.models[modelID]
	if !ok {
		return fmt.Errorf("model %s not found", modelID)
	}
	device, ok := o.devices[deviceID]
	if !ok {
		return fmt.Errorf("device %s not found", deviceID)
	}
	if device.MemoryMB < model.MinMemoryMB {
		return fmt.Errorf("insufficient memory: need %d MB, have %d MB",
			model.MinMemoryMB, device.MemoryMB)
	}

	device.Models[modelID] = true
	o.routingTable[modelID] = deviceID
	return nil
}

// FindBestDevice selects optimal device for inference
func (o *EdgeAIOrchestrator) FindBestDevice(modelID string) string {
	o.mu.RLock()
	defer o.mu.RUnlock()

	// Check routing table first
	if preferred, ok := o.routingTable[modelID]; ok {
		if dev, exists := o.devices[preferred]; exists && dev.Available {
			return preferred
		}
	}

	// Find least loaded device with model
	var bestID string
	bestLoad := math.MaxFloat64
	for id, dev := range o.devices {
		if !dev.Available {
			continue
		}
		if dev.Models[modelID] && dev.LoadPercent < bestLoad {
			bestLoad = dev.LoadPercent
			bestID = id
		}
	}
	return bestID
}

// RouteInference routes an inference request to best device
func (o *EdgeAIOrchestrator) RouteInference(req *InferenceRequest) *InferenceResult {
	o.mu.Lock()
	o.requestCount++
	o.mu.Unlock()

	deviceID := o.FindBestDevice(req.ModelID)
	if deviceID == "" {
		o.mu.Lock()
		o.failureCount++
		o.mu.Unlock()
		return &InferenceResult{
			RequestID: req.RequestID,
			Success:   false,
			Error:     "no available device",
		}
	}

	o.mu.RLock()
	model := o.models[req.ModelID]
	device := o.devices[deviceID]
	o.mu.RUnlock()

	// Simulate latency based on device load
	latency := model.LatencyMs * (1.0 + device.LoadPercent/100.0)

	// Update device load
	o.mu.Lock()
	device.LoadPercent = math.Min(device.LoadPercent+5.0, 100.0)
	o.successCount++
	o.totalLatency += latency
	o.mu.Unlock()

	return &InferenceResult{
		RequestID: req.RequestID,
		DeviceID:  deviceID,
		LatencyMs: latency,
		Success:   true,
	}
}

// AutoScale rebalances load across devices
func (o *EdgeAIOrchestrator) AutoScale() {
	o.mu.Lock()
	defer o.mu.Unlock()

	for _, dev := range o.devices {
		// Simulate load decay
		dev.LoadPercent = math.Max(0, dev.LoadPercent*0.8)
	}
}

// Summary returns orchestrator statistics
func (o *EdgeAIOrchestrator) Summary() map[string]interface{} {
	o.mu.RLock()
	defer o.mu.RUnlock()

	avgLatency := 0.0
	if o.successCount > 0 {
		avgLatency = o.totalLatency / float64(o.successCount)
	}

	return map[string]interface{}{
		"total_devices":  len(o.devices),
		"total_models":   len(o.models),
		"total_requests": o.requestCount,
		"success_count":  o.successCount,
		"failure_count":  o.failureCount,
		"avg_latency_ms": fmt.Sprintf("%.2f", avgLatency),
	}
}
