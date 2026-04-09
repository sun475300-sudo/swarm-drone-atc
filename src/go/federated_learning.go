package commbroker

import (
	"encoding/json"
	"fmt"
	"math"
	"math/rand"
	"time"
)

type ModelWeights []float64

type LocalModel struct {
	DroneID    string
	Weights    ModelWeights
	NumSamples int
	Timestamp  time.Time
	Loss       float64
}

type FederatedServer struct {
	GlobalWeights ModelWeights
	Round         int
	Clients       []string
	History       []FederationRound
}

type FederationRound struct {
	Round       int
	Timestamp   time.Time
	NumClients  int
	GlobalLoss  float64
	AvgAccuracy float64
	Convergence float64
}

func NewFederatedServer(numWeights int) *FederatedServer {
	weights := make([]float64, numWeights)
	rand.Seed(time.Now().UnixNano())
	for i := range weights {
		weights[i] = rand.NormFloat64() * 0.1
	}
	return &FederatedServer{
		GlobalWeights: weights,
		Round:         0,
		Clients:       []string{},
		History:       []FederationRound{},
	}
}

func (s *FederatedServer) RegisterClient(droneID string) {
	for _, c := range s.Clients {
		if c == droneID {
			return
		}
		s.Clients = append(s.Clients, droneID)
	}
}

func (s *FederatedServer) AggregateModels(localModels []LocalModel) ModelWeights {
	if len(localModels) == 0 {
		return s.GlobalWeights
	}

	numWeights := len(s.GlobalWeights)
	totalSamples := 0
	for _, m := range localModels {
		totalSamples += m.NumSamples
	}

	aggregated := make([]float64, numWeights)
	for _, m := range localModels {
		weight := float64(m.NumSamples) / float64(totalSamples)
		for i, w := range m.Weights {
			aggregated[i] += w * weight
		}
	}

	s.GlobalWeights = aggregated
	s.Round++

	globalLoss := 0.0
	for _, m := range localModels {
		globalLoss += m.Loss
	}
	globalLoss /= float64(len(localModels))

	round := FederationRound{
		Round:       s.Round,
		Timestamp:   time.Now(),
		NumClients:  len(localModels),
		GlobalLoss:  globalLoss,
		Convergence: s.calculateConvergence(),
	}
	s.History = append(s.History, round)

	return s.GlobalWeights
}

func (s *FederatedServer) calculateConvergence() float64 {
	if len(s.History) < 2 {
		return 1.0
	}
	recentLosses := []float64{}
	for i := max(0, len(s.History)-5); i < len(s.History); i++ {
		recentLosses = append(recentLosses, s.History[i].GlobalLoss)
	}
	if len(recentLosses) < 2 {
		return 1.0
	}

	variance := 0.0
	mean := 0.0
	for _, l := range recentLosses {
		mean += l
	}
	mean /= float64(len(recentLosses))
	for _, l := range recentLosses {
		variance += (l - mean) * (l - mean)
	}
	variance /= float64(len(recentLosses))

	return math.Min(1.0, math.Sqrt(variance)*10)
}

func SimulateLocalTraining(droneID string, globalWeights ModelWeights, localEpochs int) LocalModel {
	numWeights := len(globalWeights)
	weights := make([]float64, numWeights)
	copy(weights, globalWeights)

	numSamples := rand.Intn(100) + 50

	learningRate := 0.01
	for epoch := 0; epoch < localEpochs; epoch++ {
		for i := range weights {
			gradient := rand.NormFloat64() * 0.1
			weights[i] -= learningRate * gradient
		}
	}

	loss := 0.0
	for _, w := range weights {
		loss += w * w
	}
	loss /= float64(numWeights)

	return LocalModel{
		DroneID:    droneID,
		Weights:    weights,
		NumSamples: numSamples,
		Timestamp:  time.Now(),
		Loss:       loss,
	}
}

func (s *FederatedServer) GetStatus() map[string]interface{} {
	return map[string]interface{}{
		"round":       s.Round,
		"num_clients": len(s.Clients),
		"convergence": s.History[len(s.History)-1].Convergence,
		"global_loss": s.History[len(s.History)-1].GlobalLoss,
		"num_rounds":  len(s.History),
	}
}

func main() {
	server := NewFederatedServer(100)

	droneIDs := []string{"DRONE-001", "DRONE-002", "DRONE-003", "DRONE-004", "DRONE-005"}
	for _, id := range droneIDs {
		server.RegisterClient(id)
	}

	fmt.Println("=== Federated Learning Simulation ===")
	fmt.Printf("Initial clients: %d\n\n", len(server.Clients))

	for round := 1; round <= 10; round++ {
		fmt.Printf("--- Round %d ---\n", round)

		localModels := []LocalModel{}
		selectedClients := []string{}

		numSelected := min(3, len(server.Clients))
		indices := rand.Perm(len(server.Clients))[:numSelected]
		for _, idx := range indices {
			droneID := server.Clients[idx]
			selectedClients = append(selectedClients, droneID)

			model := SimulateLocalTraining(droneID, server.GlobalWeights, 5)
			localModels = append(localModels, model)

			fmt.Printf("  %s: samples=%d, loss=%.4f\n",
				droneID, model.NumSamples, model.Loss)
		}

		server.AggregateModels(localModels)
		status := server.GetStatus()

		fmt.Printf("  Aggregated: clients=%d, loss=%.4f, convergence=%.2f%%\n\n",
			status["num_clients"], status["global_loss"], status["convergence"].(float64)*100)
	}

	finalStatus := server.GetStatus()
	fmt.Println("=== Final Status ===")
	jsonBytes, _ := json.MarshalIndent(finalStatus, "", "  ")
	fmt.Println(string(jsonBytes))
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
