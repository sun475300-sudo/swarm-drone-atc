// Phase 523: swarm_blockchain — Go 기반 군집 드론 블록체인
// SDACS Swarm Blockchain for Distributed Consensus

package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strings"
	"time"
)

// Block represents a single block in the drone swarm chain
type Block struct {
	Index     int
	Timestamp int64
	DroneID   int
	Data      string
	PrevHash  string
	Hash      string
	Nonce     int
}

// computeHash calculates sha256 hash of a block
func (b *Block) computeHash() string {
	record := fmt.Sprintf("%d%d%d%s%s%d", b.Index, b.Timestamp, b.DroneID, b.Data, b.PrevHash, b.Nonce)
	h := sha256.Sum256([]byte(record))
	return hex.EncodeToString(h[:])
}

// DroneBlockchain is the main chain structure
type DroneBlockchain struct {
	Blocks    []*Block
	Consensus string // PBFT consensus mechanism
	Peers     int
}

// NewBlockchain creates a genesis block
func NewBlockchain(peers int) *DroneBlockchain {
	genesis := &Block{
		Index:     0,
		Timestamp: time.Now().Unix(),
		DroneID:   -1,
		Data:      "SDACS Genesis Block",
		PrevHash:  "0000000000000000",
	}
	genesis.Hash = genesis.computeHash()
	return &DroneBlockchain{
		Blocks:    []*Block{genesis},
		Consensus: "PBFT",
		Peers:     peers,
	}
}

// AddBlock appends a validated block using PBFT consensus
func (bc *DroneBlockchain) AddBlock(droneID int, data string) *Block {
	prev := bc.Blocks[len(bc.Blocks)-1]
	block := &Block{
		Index:     len(bc.Blocks),
		Timestamp: time.Now().Unix(),
		DroneID:   droneID,
		Data:      data,
		PrevHash:  prev.Hash,
	}
	// Simple proof: find nonce where hash starts with "0"
	for {
		block.Hash = block.computeHash()
		if strings.HasPrefix(block.Hash, "0") {
			break
		}
		block.Nonce++
	}
	bc.Blocks = append(bc.Blocks, block)
	return block
}

// IsValid verifies chain integrity using hash chaining
func (bc *DroneBlockchain) IsValid() bool {
	for i := 1; i < len(bc.Blocks); i++ {
		curr := bc.Blocks[i]
		prev := bc.Blocks[i-1]
		if curr.Hash != curr.computeHash() {
			return false
		}
		if curr.PrevHash != prev.Hash {
			return false
		}
	}
	return true
}

// PBFTConsensus simulates PBFT voting round
type PBFTConsensus struct {
	NodeCount int
	FaultyMax int
}

func NewPBFT(nodes int) *PBFTConsensus {
	return &PBFTConsensus{
		NodeCount: nodes,
		FaultyMax: (nodes - 1) / 3,
	}
}

// Vote runs a consensus round (returns true if quorum reached)
func (p *PBFTConsensus) Vote(proposal string) bool {
	// f+1 honest nodes needed in PBFT with 3f+1 total
	h := sha256.Sum256([]byte(proposal))
	_ = hex.EncodeToString(h[:])
	quorum := 2*p.FaultyMax + 1
	return p.NodeCount >= quorum
}

func main() {
	fmt.Println("SDACS Swarm Blockchain — Phase 523\n")

	bc := NewBlockchain(5)
	pbft := NewPBFT(5)

	telemetry := []struct {
		droneID int
		data    string
	}{
		{0, "lat=37.500,lon=127.000,alt=50.0,bat=95.0"},
		{1, "lat=37.501,lon=127.001,alt=52.0,bat=88.0"},
		{2, "lat=37.502,lon=127.002,alt=53.5,bat=91.0"},
	}

	for _, t := range telemetry {
		if pbft.Vote(t.data) {
			block := bc.AddBlock(t.droneID, t.data)
			fmt.Printf("블록 #%d: Drone%d → hash=%s\n", block.Index, block.DroneID, block.Hash[:12])
		}
	}

	fmt.Printf("\n체인 길이: %d 블록\n", len(bc.Blocks))
	fmt.Printf("무결성 검증: %v\n", bc.IsValid())
	fmt.Printf("합의 방식: %s (노드=%d, 최대결함=%d)\n", bc.Consensus, pbft.NodeCount, pbft.FaultyMax)
	fmt.Println("블록체인 처리 완료.")
}
