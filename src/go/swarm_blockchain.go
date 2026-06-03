// Phase 523: Swarm Blockchain — Go
// SDACS PBFT consensus-based distributed ledger for drone flight logs

package blockchain

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"time"
)

// Phase 523 marker — swarm blockchain with PBFT consensus

// FlightRecord is an immutable drone flight log entry
type FlightRecord struct {
	DroneID    string    `json:"drone_id"`
	Timestamp  time.Time `json:"timestamp"`
	Latitude   float64   `json:"lat"`
	Longitude  float64   `json:"lon"`
	Altitude   float64   `json:"alt"`
	Speed      float64   `json:"speed"`
	Battery    float64   `json:"battery"`
	EventType  string    `json:"event_type"`
}

// Block is a blockchain block containing flight records
type Block struct {
	Index        uint64         `json:"index"`
	Timestamp    time.Time      `json:"timestamp"`
	Records      []FlightRecord `json:"records"`
	PrevHash     string         `json:"prev_hash"`
	Hash         string         `json:"hash"`
	Nonce        uint64         `json:"nonce"`
	ValidatorID  string         `json:"validator_id"`
}

// ComputeHash computes SHA-256 hash of the block
func (b *Block) ComputeHash() string {
	data, _ := json.Marshal(struct {
		Index       uint64
		Timestamp   time.Time
		Records     []FlightRecord
		PrevHash    string
		Nonce       uint64
		ValidatorID string
	}{b.Index, b.Timestamp, b.Records, b.PrevHash, b.Nonce, b.ValidatorID})

	h := sha256.Sum256(data)
	return hex.EncodeToString(h[:])
}

// PBFTMessage is a PBFT consensus protocol message
type PBFTPhase string

const (
	PhasePrePrepare PBFTPhase = "PRE-PREPARE"
	PhasePrepare    PBFTPhase = "PREPARE"
	PhaseCommit     PBFTPhase = "COMMIT"
)

type PBFTMessage struct {
	Phase     PBFTPhase `json:"phase"`
	View      uint64    `json:"view"`
	SeqNum    uint64    `json:"seq"`
	BlockHash string    `json:"block_hash"`
	NodeID    string    `json:"node_id"`
	Signature string    `json:"sig"`
}

// ConsensusState tracks PBFT state for a block
type ConsensusState struct {
	Block      *Block
	Prepares   map[string]bool
	Commits    map[string]bool
	Committed  bool
}

// SwarmBlockchain is a distributed flight log ledger
type SwarmBlockchain struct {
	mu          sync.RWMutex
	chain       []*Block
	nodeID      string
	nodeCount   int
	pendingRecords []FlightRecord
	consensusMap   map[string]*ConsensusState
}

// NewSwarmBlockchain creates a new blockchain with genesis block
func NewSwarmBlockchain(nodeID string, nodeCount int) *SwarmBlockchain {
	genesis := &Block{
		Index:       0,
		Timestamp:   time.Now().UTC(),
		Records:     []FlightRecord{},
		PrevHash:    "0000000000000000",
		ValidatorID: nodeID,
	}
	genesis.Hash = genesis.ComputeHash()

	return &SwarmBlockchain{
		chain:        []*Block{genesis},
		nodeID:       nodeID,
		nodeCount:    nodeCount,
		consensusMap: make(map[string]*ConsensusState),
	}
}

// AddRecord adds a flight record to the pending pool
func (bc *SwarmBlockchain) AddRecord(r FlightRecord) {
	bc.mu.Lock()
	defer bc.mu.Unlock()
	bc.pendingRecords = append(bc.pendingRecords, r)
}

// ProposeBlock creates a new block from pending records
func (bc *SwarmBlockchain) ProposeBlock() (*Block, error) {
	bc.mu.Lock()
	defer bc.mu.Unlock()

	if len(bc.pendingRecords) == 0 {
		return nil, errors.New("no pending records")
	}

	prev := bc.chain[len(bc.chain)-1]
	block := &Block{
		Index:       prev.Index + 1,
		Timestamp:   time.Now().UTC(),
		Records:     make([]FlightRecord, len(bc.pendingRecords)),
		PrevHash:    prev.Hash,
		ValidatorID: bc.nodeID,
	}
	copy(block.Records, bc.pendingRecords)
	block.Hash = block.ComputeHash()
	bc.pendingRecords = nil

	bc.consensusMap[block.Hash] = &ConsensusState{
		Block:    block,
		Prepares: make(map[string]bool),
		Commits:  make(map[string]bool),
	}

	return block, nil
}

// HandlePBFTMessage processes a PBFT consensus message
func (bc *SwarmBlockchain) HandlePBFTMessage(msg PBFTMessage) error {
	bc.mu.Lock()
	defer bc.mu.Unlock()

	state, ok := bc.consensusMap[msg.BlockHash]
	if !ok {
		return fmt.Errorf("unknown block hash: %s", msg.BlockHash)
	}

	quorum := (2*bc.nodeCount)/3 + 1

	switch msg.Phase {
	case PhasePrePrepare:
		// Acknowledge pre-prepare
	case PhasePrepare:
		state.Prepares[msg.NodeID] = true
	case PhaseCommit:
		state.Commits[msg.NodeID] = true
		if len(state.Commits) >= quorum && !state.Committed {
			state.Committed = true
			bc.chain = append(bc.chain, state.Block)
			delete(bc.consensusMap, msg.BlockHash)
		}
	}
	return nil
}

// GetChain returns a copy of the blockchain
func (bc *SwarmBlockchain) GetChain() []*Block {
	bc.mu.RLock()
	defer bc.mu.RUnlock()
	result := make([]*Block, len(bc.chain))
	copy(result, bc.chain)
	return result
}

// Validate verifies the integrity of the entire chain
func (bc *SwarmBlockchain) Validate() bool {
	bc.mu.RLock()
	defer bc.mu.RUnlock()

	for i := 1; i < len(bc.chain); i++ {
		curr := bc.chain[i]
		prev := bc.chain[i-1]
		if curr.PrevHash != prev.Hash {
			return false
		}
		if curr.Hash != curr.ComputeHash() {
			return false
		}
	}
	return true
}

// Stats returns blockchain statistics
func (bc *SwarmBlockchain) Stats() map[string]interface{} {
	bc.mu.RLock()
	defer bc.mu.RUnlock()

	totalRecords := 0
	for _, b := range bc.chain {
		totalRecords += len(b.Records)
	}
	return map[string]interface{}{
		"length":          len(bc.chain),
		"total_records":   totalRecords,
		"pending_records": len(bc.pendingRecords),
		"pending_consensus": len(bc.consensusMap),
		"node_id":         bc.nodeID,
	}
}
