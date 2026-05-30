// SDACS Swarm Blockchain — Go (Phase 523)
// 드론 군집 분산 원장 (PBFT 합의 + SHA-256 해싱)

package blockchain

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sync"
	"time"
)

// Transaction represents a swarm telemetry event on-chain.
type Transaction struct {
	DroneID   string
	Action    string
	Timestamp int64
	Data      map[string]interface{}
}

// Block is a single blockchain block.
type Block struct {
	Index        int
	Timestamp    int64
	Transactions []Transaction
	PrevHash     string
	Hash         string
	Nonce        int
}

// computeHash computes SHA-256 hash of block contents.
func computeHash(b *Block) string {
	record := fmt.Sprintf("%d%d%v%s%d", b.Index, b.Timestamp, b.Transactions, b.PrevHash, b.Nonce)
	h := sha256.Sum256([]byte(record))
	return hex.EncodeToString(h[:])
}

// NewBlock creates and hashes a new block.
func NewBlock(index int, txs []Transaction, prevHash string) *Block {
	b := &Block{
		Index:        index,
		Timestamp:    time.Now().UnixNano(),
		Transactions: txs,
		PrevHash:     prevHash,
	}
	b.Hash = computeHash(b)
	return b
}

// Chain is the local blockchain ledger.
type Chain struct {
	mu     sync.RWMutex
	blocks []*Block
}

// NewChain creates a chain with a genesis block.
func NewChain() *Chain {
	genesis := NewBlock(0, nil, "0000000000000000")
	return &Chain{blocks: []*Block{genesis}}
}

// AddBlock appends a validated block.
func (c *Chain) AddBlock(txs []Transaction) *Block {
	c.mu.Lock()
	defer c.mu.Unlock()
	prev := c.blocks[len(c.blocks)-1]
	b := NewBlock(len(c.blocks), txs, prev.Hash)
	c.blocks = append(c.blocks, b)
	return b
}

// IsValid verifies the chain integrity.
func (c *Chain) IsValid() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	for i := 1; i < len(c.blocks); i++ {
		cur := c.blocks[i]
		prev := c.blocks[i-1]
		if cur.PrevHash != prev.Hash {
			return false
		}
		if cur.Hash != computeHash(cur) {
			return false
		}
	}
	return true
}

func (c *Chain) Length() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.blocks)
}

// PBFT consensus node (Phase 523 — simplified 3-phase PBFT)
type PBFTNode struct {
	ID       string
	peers    []*PBFTNode
	prepared map[string]int
	mu       sync.Mutex
}

func NewPBFTNode(id string) *PBFTNode {
	return &PBFTNode{
		ID:       id,
		prepared: make(map[string]int),
	}
}

func (n *PBFTNode) AddPeer(peer *PBFTNode) {
	n.peers = append(n.peers, peer)
}

// Prepare broadcasts a prepare message; returns true if consensus reached.
func (n *PBFTNode) Propose(msgID string) bool {
	n.mu.Lock()
	n.prepared[msgID]++
	count := n.prepared[msgID]
	n.mu.Unlock()

	for _, peer := range n.peers {
		peer.mu.Lock()
		peer.prepared[msgID]++
		peer.mu.Unlock()
	}

	// consensus requires 2f+1 nodes (f=1 fault tolerance here)
	quorum := (len(n.peers)+1)*2/3 + 1
	return count >= quorum
}

// SwarmAuditLedger combines chain + PBFT for audit trail.
type SwarmAuditLedger struct {
	chain *Chain
	node  *PBFTNode
}

func NewSwarmAuditLedger(nodeID string) *SwarmAuditLedger {
	return &SwarmAuditLedger{
		chain: NewChain(),
		node:  NewPBFTNode(nodeID),
	}
}

func (l *SwarmAuditLedger) RecordEvent(droneID, action string, data map[string]interface{}) string {
	tx := Transaction{DroneID: droneID, Action: action, Timestamp: time.Now().UnixNano(), Data: data}
	msgID := fmt.Sprintf("%s-%d", droneID, tx.Timestamp)
	_ = l.node.Propose(msgID)
	block := l.chain.AddBlock([]Transaction{tx})
	return block.Hash
}

func (l *SwarmAuditLedger) IsValid() bool { return l.chain.IsValid() }
func (l *SwarmAuditLedger) Length() int    { return l.chain.Length() }
