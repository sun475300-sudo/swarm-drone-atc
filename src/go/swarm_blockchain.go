// Phase 523: Swarm Blockchain — PBFT consensus for drone fleet
// 군집 드론 블록체인 합의 프로토콜 구현
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"math/rand"
	"time"
)

// Block represents a single block in the drone ledger chain.
type Block struct {
	Index     int
	Timestamp int64
	Data      string
	PrevHash  string
	Hash      string
	Nonce     int
}

// computeHash returns sha256 hash string for a block.
func computeHash(b Block) string {
	record := fmt.Sprintf("%d%d%s%s%d", b.Index, b.Timestamp, b.Data, b.PrevHash, b.Nonce)
	h := sha256.Sum256([]byte(record))
	return hex.EncodeToString(h[:])
}

// newBlock creates and hashes a new block.
func newBlock(index int, data, prevHash string) Block {
	b := Block{
		Index:     index,
		Timestamp: time.Now().UnixNano(),
		Data:      data,
		PrevHash:  prevHash,
		Nonce:     rand.Intn(100000),
	}
	b.Hash = computeHash(b)
	return b
}

// PBFTMessage encodes a PBFT consensus message.
type PBFTMessage struct {
	Phase  string // pre-prepare, prepare, commit
	View   int
	SeqNum int
	Digest string
	NodeID int
}

// PBFTNode represents a single consensus node in the swarm.
type PBFTNode struct {
	ID       int
	IsPrimary bool
	Messages []PBFTMessage
}

// Prepare adds a prepare message for PBFT round.
func (n *PBFTNode) Prepare(view, seq int, digest string) {
	msg := PBFTMessage{Phase: "prepare", View: view, SeqNum: seq, Digest: digest, NodeID: n.ID}
	n.Messages = append(n.Messages, msg)
}

// Commit adds a commit message to the PBFT log.
func (n *PBFTNode) Commit(view, seq int, digest string) {
	msg := PBFTMessage{Phase: "commit", View: view, SeqNum: seq, Digest: digest, NodeID: n.ID}
	n.Messages = append(n.Messages, msg)
}

// SwarmBlockchain maintains the drone mission ledger with PBFT consensus.
type SwarmBlockchain struct {
	Chain []Block
	Nodes []*PBFTNode
	F     int // Byzantine fault tolerance: tolerates f faulty nodes
}

// NewSwarmBlockchain initialises with genesis block and n PBFT nodes.
func NewSwarmBlockchain(n int) *SwarmBlockchain {
	genesis := Block{Index: 0, Timestamp: time.Now().UnixNano(), Data: "genesis", PrevHash: "0"}
	genesis.Hash = computeHash(genesis)
	nodes := make([]*PBFTNode, n)
	for i := range nodes {
		nodes[i] = &PBFTNode{ID: i, IsPrimary: i == 0}
	}
	return &SwarmBlockchain{Chain: []Block{genesis}, Nodes: nodes, F: (n - 1) / 3}
}

// AddMissionLog appends a validated mission entry via PBFT consensus.
func (sc *SwarmBlockchain) AddMissionLog(entry string) bool {
	prev := sc.Chain[len(sc.Chain)-1]
	b := newBlock(len(sc.Chain), entry, prev.Hash)
	// Simulate PBFT: collect 2f+1 commits
	quorum := 2*sc.F + 1
	commits := 0
	for _, node := range sc.Nodes {
		node.Commit(0, b.Index, b.Hash)
		commits++
		if commits >= quorum {
			break
		}
	}
	if commits >= quorum {
		sc.Chain = append(sc.Chain, b)
		return true
	}
	return false
}

// Validate checks chain integrity using sha256 hashes.
func (sc *SwarmBlockchain) Validate() bool {
	for i := 1; i < len(sc.Chain); i++ {
		curr := sc.Chain[i]
		prev := sc.Chain[i-1]
		if curr.Hash != computeHash(curr) {
			return false
		}
		if curr.PrevHash != prev.Hash {
			return false
		}
	}
	return true
}

func main() {
	fmt.Println("Phase 523: Swarm Blockchain — 드론 미션 원장")
	sc := NewSwarmBlockchain(4)
	sc.AddMissionLog("drone-0 patrolZone alpha")
	sc.AddMissionLog("drone-1 deliveryComplete sector-7")
	fmt.Printf("Chain length: %d, Valid: %v\n", len(sc.Chain), sc.Validate())
}
