// Phase 523: Swarm Drone Blockchain Consensus
// PBFT consensus protocol with SHA256 hashing
// SDACS Distributed Ledger Module

package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"
)

// Block represents a ledger entry in the swarm blockchain
type Block struct {
	Index     int
	Timestamp int64
	Data      string
	PrevHash  string
	Hash      string
	Validator string
}

// computeHash computes SHA256 hash of block fields
func computeHash(b Block) string {
	record := fmt.Sprintf("%d%d%s%s%s", b.Index, b.Timestamp, b.Data, b.PrevHash, b.Validator)
	h := sha256.New()
	h.Write([]byte(record))
	return hex.EncodeToString(h.Sum(nil))
}

// SwarmBlockchain implements the distributed ledger
type SwarmBlockchain struct {
	Chain     []Block
	DroneID   string
	consensus *PBFTConsensus
}

// NewSwarmBlockchain creates a new blockchain with genesis block
func NewSwarmBlockchain(droneID string, numNodes int) *SwarmBlockchain {
	genesis := Block{
		Index:     0,
		Timestamp: time.Now().Unix(),
		Data:      "Genesis Block - SDACS v523",
		PrevHash:  "0000000000000000",
		Validator: droneID,
	}
	genesis.Hash = computeHash(genesis)
	return &SwarmBlockchain{
		Chain:     []Block{genesis},
		DroneID:   droneID,
		consensus: NewPBFTConsensus(numNodes),
	}
}

// AddBlock adds a validated block after PBFT consensus
func (bc *SwarmBlockchain) AddBlock(data string) Block {
	prev := bc.Chain[len(bc.Chain)-1]
	newBlock := Block{
		Index:     prev.Index + 1,
		Timestamp: time.Now().Unix(),
		Data:      data,
		PrevHash:  prev.Hash,
		Validator: bc.DroneID,
	}
	newBlock.Hash = computeHash(newBlock)
	if bc.consensus.Agree(newBlock) {
		bc.Chain = append(bc.Chain, newBlock)
	}
	return newBlock
}

// IsValid verifies the chain integrity using SHA256 hashes
func (bc *SwarmBlockchain) IsValid() bool {
	for i := 1; i < len(bc.Chain); i++ {
		cur := bc.Chain[i]
		prev := bc.Chain[i-1]
		if cur.Hash != computeHash(cur) {
			return false
		}
		if cur.PrevHash != prev.Hash {
			return false
		}
	}
	return true
}

// PBFTConsensus implements Practical Byzantine Fault Tolerance
type PBFTConsensus struct {
	NumNodes    int
	FaultLimit  int
	PrepareVotes map[string]int
}

// NewPBFTConsensus creates a PBFT instance with f = (n-1)/3
func NewPBFTConsensus(n int) *PBFTConsensus {
	return &PBFTConsensus{
		NumNodes:     n,
		FaultLimit:   (n - 1) / 3,
		PrepareVotes: make(map[string]int),
	}
}

// Agree runs PBFT prepare-commit and returns consensus result
func (p *PBFTConsensus) Agree(block Block) bool {
	// Simulate PBFT: require 2f+1 votes for consensus
	data, _ := json.Marshal(block)
	h := sha256.New()
	h.Write(data)
	digest := hex.EncodeToString(h.Sum(nil))
	p.PrepareVotes[digest]++
	required := 2*p.FaultLimit + 1
	return p.PrepareVotes[digest] >= required || p.NumNodes <= 1
}

func main() {
	fmt.Println("SDACS Swarm Blockchain v523")
	bc := NewSwarmBlockchain("drone_leader", 4)
	bc.AddBlock("telemetry:drone_001:alt=100m")
	bc.AddBlock("conflict:resolved:APF")
	fmt.Printf("Chain length: %d\n", len(bc.Chain))
	fmt.Printf("Chain valid: %v\n", bc.IsValid())
	fmt.Printf("PBFT consensus with sha256 hashing active\n")
}
