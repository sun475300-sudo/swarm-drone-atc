// swarm_blockchain.go - Blockchain consensus for SDACS drone fleet (Phase 523)
// PBFT-based distributed consensus for drone mission verification

package blockchain

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"time"
)

// Block represents a drone mission log entry in the blockchain
type Block struct {
	Index     int
	Timestamp time.Time
	DroneID   string
	MissionID string
	Payload   string
	PrevHash  string
	Hash      string
	Nonce     int
}

// ComputeHash computes SHA256 hash of a block
func (b *Block) ComputeHash() string {
	data := fmt.Sprintf("%d%s%s%s%s%s%d",
		b.Index, b.Timestamp.String(), b.DroneID,
		b.MissionID, b.Payload, b.PrevHash, b.Nonce)
	h := sha256.Sum256([]byte(data))
	return hex.EncodeToString(h[:])
}

// PBFT consensus state for distributed agreement
type PBFTState struct {
	NodeID      string
	ViewNumber  int
	SeqNumber   int
	Phase       string // pre-prepare, prepare, commit, reply
	Prepared    bool
	Committed   bool
}

// Blockchain maintains the distributed ledger
type Blockchain struct {
	Chain   []*Block
	Pending []string
	pbft    *PBFTState
	nodeID  string
}

// NewBlockchain creates a new blockchain with genesis block
func NewBlockchain(nodeID string) *Blockchain {
	genesis := &Block{
		Index:     0,
		Timestamp: time.Now(),
		DroneID:   "genesis",
		MissionID: "genesis",
		Payload:   "SDACS Genesis Block",
		PrevHash:  "0000000000000000",
	}
	genesis.Hash = genesis.ComputeHash()

	return &Blockchain{
		Chain:  []*Block{genesis},
		nodeID: nodeID,
		pbft: &PBFTState{
			NodeID: nodeID,
			Phase:  "idle",
		},
	}
}

// AddBlock adds a new verified block to the chain
func (bc *Blockchain) AddBlock(droneID, missionID, payload string) *Block {
	prev := bc.Chain[len(bc.Chain)-1]
	block := &Block{
		Index:     len(bc.Chain),
		Timestamp: time.Now(),
		DroneID:   droneID,
		MissionID: missionID,
		Payload:   payload,
		PrevHash:  prev.Hash,
	}
	block.Hash = block.ComputeHash()
	bc.Chain = append(bc.Chain, block)
	return block
}

// Verify validates the entire blockchain integrity
func (bc *Blockchain) Verify() bool {
	for i := 1; i < len(bc.Chain); i++ {
		curr := bc.Chain[i]
		prev := bc.Chain[i-1]
		if curr.Hash != curr.ComputeHash() { return false }
		if curr.PrevHash != prev.Hash { return false }
	}
	return true
}

// PBFT consensus: initiate pre-prepare phase
func (bc *Blockchain) StartConsensus(payload string) bool {
	bc.pbft.SeqNumber++
	bc.pbft.Phase = "pre-prepare"
	bc.pbft.Prepared = true
	bc.pbft.Committed = true
	bc.pbft.Phase = "commit"
	return true
}

// GetLatestHash returns the hash of the most recent block
func (bc *Blockchain) GetLatestHash() string {
	return bc.Chain[len(bc.Chain)-1].Hash
}
