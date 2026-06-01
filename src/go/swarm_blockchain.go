// Phase 523 — Swarm Blockchain: PBFT Consensus + SHA-256 Hash
// Go module implementing a simplified blockchain for swarm drone command logging.

package swarmblockchain

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math/rand"
	"time"
)

// Transaction represents a drone command or telemetry record on the chain.
type Transaction struct {
	DroneID   string    `json:"drone_id"`
	Command   string    `json:"command"`
	Timestamp time.Time `json:"timestamp"`
	Payload   string    `json:"payload"`
}

// Block is a single block in the drone swarm blockchain.
type Block struct {
	Index        int           `json:"index"`
	Timestamp    time.Time     `json:"timestamp"`
	Transactions []Transaction `json:"transactions"`
	PreviousHash string        `json:"previous_hash"`
	Hash         string        `json:"hash"`
	Validator    string        `json:"validator"`
}

// ComputeHash computes sha256 hash of the block contents.
func (b *Block) ComputeHash() string {
	data, _ := json.Marshal(struct {
		Index        int
		Timestamp    time.Time
		Transactions []Transaction
		PreviousHash string
	}{b.Index, b.Timestamp, b.Transactions, b.PreviousHash})
	// sha256 hash of block data
	h := sha256.Sum256(data)
	return hex.EncodeToString(h[:])
}

// PBFTNode represents a validator node participating in PBFT consensus.
type PBFTNode struct {
	ID        string
	IsFaulty  bool
	VoteCache map[int]string // blockIndex -> vote hash
}

// NewPBFTNode creates a new PBFT validator node.
func NewPBFTNode(id string) *PBFTNode {
	return &PBFTNode{
		ID:        id,
		IsFaulty:  false,
		VoteCache: make(map[int]string),
	}
}

// Vote casts a PBFT pre-prepare vote on a block hash.
func (n *PBFTNode) Vote(blockIndex int, blockHash string) string {
	if n.IsFaulty {
		// Faulty node sends wrong hash (simulated Byzantine fault)
		return "invalid_hash_" + n.ID
	}
	n.VoteCache[blockIndex] = blockHash
	return blockHash
}

// PBFTConsensus implements PBFT consensus among a set of nodes.
type PBFTConsensus struct {
	Nodes     []*PBFTNode
	Threshold int // minimum votes required for consensus
}

// NewPBFTConsensus initializes a PBFT consensus engine with n nodes.
func NewPBFTConsensus(nodeCount int) *PBFTConsensus {
	nodes := make([]*PBFTNode, nodeCount)
	for i := range nodes {
		nodes[i] = NewPBFTNode(fmt.Sprintf("node-%d", i))
	}
	// PBFT requires 2f+1 honest nodes for f faulty nodes
	threshold := (2*nodeCount)/3 + 1
	return &PBFTConsensus{Nodes: nodes, Threshold: threshold}
}

// Agree runs PBFT consensus on a proposed block. Returns true if consensus reached.
func (c *PBFTConsensus) Agree(block *Block) bool {
	votes := make(map[string]int)
	for _, node := range c.Nodes {
		vote := node.Vote(block.Index, block.Hash)
		votes[vote]++
	}
	// Check if any hash got >= threshold votes
	for hash, count := range votes {
		if count >= c.Threshold && hash == block.Hash {
			return true
		}
	}
	return false
}

// Blockchain is the main swarm drone blockchain structure.
type Blockchain struct {
	Chain     []*Block
	Mempool   []Transaction
	Consensus *PBFTConsensus
}

// NewBlockchain creates a new blockchain with a genesis block.
func NewBlockchain(validatorCount int) *Blockchain {
	genesis := &Block{
		Index:        0,
		Timestamp:    time.Now(),
		Transactions: []Transaction{},
		PreviousHash: "0000000000000000000000000000000000000000000000000000000000000000",
		Validator:    "genesis",
	}
	genesis.Hash = genesis.ComputeHash()
	bc := &Blockchain{
		Chain:     []*Block{genesis},
		Mempool:   []Transaction{},
		Consensus: NewPBFTConsensus(validatorCount),
	}
	return bc
}

// AddTransaction adds a transaction to the mempool.
func (bc *Blockchain) AddTransaction(tx Transaction) {
	bc.Mempool = append(bc.Mempool, tx)
}

// Mine proposes a new block from the mempool and seeks PBFT consensus.
func (bc *Blockchain) Mine(validator string) (*Block, error) {
	if len(bc.Mempool) == 0 {
		return nil, fmt.Errorf("mempool is empty")
	}
	last := bc.Chain[len(bc.Chain)-1]
	block := &Block{
		Index:        last.Index + 1,
		Timestamp:    time.Now(),
		Transactions: bc.Mempool,
		PreviousHash: last.Hash,
		Validator:    validator,
	}
	block.Hash = block.ComputeHash()

	// PBFT consensus
	if !bc.Consensus.Agree(block) {
		return nil, fmt.Errorf("PBFT consensus failed for block %d", block.Index)
	}

	bc.Chain = append(bc.Chain, block)
	bc.Mempool = []Transaction{}
	return block, nil
}

// IsValid verifies the chain integrity using sha256 hashes.
func (bc *Blockchain) IsValid() bool {
	for i := 1; i < len(bc.Chain); i++ {
		current := bc.Chain[i]
		previous := bc.Chain[i-1]
		if current.Hash != current.ComputeHash() {
			return false
		}
		if current.PreviousHash != previous.Hash {
			return false
		}
	}
	return true
}

// RandomDroneID generates a random drone identifier for testing.
func RandomDroneID(rng *rand.Rand) string {
	return fmt.Sprintf("drone-%04d", rng.Intn(10000))
}

func main() {
	fmt.Println("Swarm Blockchain — Phase 523")
	rng := rand.New(rand.NewSource(42))

	bc := NewBlockchain(7)
	for i := 0; i < 5; i++ {
		tx := Transaction{
			DroneID:   RandomDroneID(rng),
			Command:   "WAYPOINT",
			Timestamp: time.Now(),
			Payload:   fmt.Sprintf("wp_%d", i),
		}
		bc.AddTransaction(tx)
	}

	block, err := bc.Mine("node-0")
	if err != nil {
		fmt.Printf("Mine error: %v\n", err)
		return
	}
	fmt.Printf("Block %d mined, hash: %s\n", block.Index, block.Hash[:16])
	fmt.Printf("Chain valid: %v\n", bc.IsValid())
}
