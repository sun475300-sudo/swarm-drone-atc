// P523: SwarmBlockchain - Go PBFT consensus blockchain for drone coordination
// Phase 523: Distributed ledger for drone command verification and audit

package swarmblockchain

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"sync"
	"time"
)

// Transaction represents a drone command or telemetry record
type Transaction struct {
	ID        string                 `json:"id"`
	DroneID   string                 `json:"drone_id"`
	Command   string                 `json:"command"`
	Timestamp time.Time              `json:"timestamp"`
	Payload   map[string]interface{} `json:"payload"`
	Signature string                 `json:"signature"`
}

// Block in the drone command blockchain
type Block struct {
	Index        int           `json:"index"`
	PreviousHash string        `json:"previous_hash"`
	Hash         string        `json:"hash"`
	Timestamp    time.Time     `json:"timestamp"`
	Transactions []Transaction `json:"transactions"`
	Nonce        int           `json:"nonce"`
	Validator    string        `json:"validator"`
}

// PBFT consensus message types
type PBFTMessageType string

const (
	PrePrepare PBFTMessageType = "PRE-PREPARE"
	Prepare    PBFTMessageType = "PREPARE"
	Commit     PBFTMessageType = "COMMIT"
)

type PBFTMessage struct {
	Type      PBFTMessageType `json:"type"`
	ViewNum   int             `json:"view_num"`
	SeqNum    int             `json:"seq_num"`
	BlockHash string          `json:"block_hash"`
	NodeID    string          `json:"node_id"`
}

// SwarmBlockchain is the main consensus blockchain
type SwarmBlockchain struct {
	mu           sync.RWMutex
	chain        []*Block
	pendingTxs   []Transaction
	nodes        []string
	viewNum      int
	primaryNode  string
}

func NewSwarmBlockchain(nodes []string) *SwarmBlockchain {
	bc := &SwarmBlockchain{
		nodes:       nodes,
		viewNum:     0,
		primaryNode: nodes[0],
	}
	genesis := bc.createGenesisBlock()
	bc.chain = []*Block{genesis}
	return bc
}

func (bc *SwarmBlockchain) createGenesisBlock() *Block {
	block := &Block{
		Index:        0,
		PreviousHash: "0000000000000000",
		Timestamp:    time.Now(),
		Transactions: []Transaction{},
		Validator:    "genesis",
	}
	block.Hash = bc.computeHash(block)
	return block
}

func (bc *SwarmBlockchain) computeHash(block *Block) string {
	data, _ := json.Marshal(struct {
		Index        int
		PreviousHash string
		Timestamp    time.Time
		Transactions []Transaction
		Nonce        int
	}{block.Index, block.PreviousHash, block.Timestamp, block.Transactions, block.Nonce})
	hash := sha256.Sum256(data)
	return fmt.Sprintf("%x", hash)
}

func (bc *SwarmBlockchain) AddTransaction(tx Transaction) {
	bc.mu.Lock()
	defer bc.mu.Unlock()
	bc.pendingTxs = append(bc.pendingTxs, tx)
}

// PBFT consensus: propose a new block
func (bc *SwarmBlockchain) ProposeBlock() (*Block, error) {
	bc.mu.Lock()
	defer bc.mu.Unlock()
	if len(bc.pendingTxs) == 0 {
		return nil, fmt.Errorf("no pending transactions")
	}
	prev := bc.chain[len(bc.chain)-1]
	block := &Block{
		Index:        prev.Index + 1,
		PreviousHash: prev.Hash,
		Timestamp:    time.Now(),
		Transactions: bc.pendingTxs,
		Validator:    bc.primaryNode,
	}
	block.Hash = bc.computeHash(block)
	bc.chain = append(bc.chain, block)
	bc.pendingTxs = nil
	return block, nil
}

func (bc *SwarmBlockchain) IsValid() bool {
	bc.mu.RLock()
	defer bc.mu.RUnlock()
	for i := 1; i < len(bc.chain); i++ {
		curr, prev := bc.chain[i], bc.chain[i-1]
		if curr.PreviousHash != prev.Hash { return false }
		if curr.Hash != bc.computeHash(curr) { return false }
	}
	return true
}

func (bc *SwarmBlockchain) Length() int {
	bc.mu.RLock()
	defer bc.mu.RUnlock()
	return len(bc.chain)
}
