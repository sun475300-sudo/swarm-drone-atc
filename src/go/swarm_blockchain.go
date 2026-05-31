// Package swarmchain implements Phase 523 — PBFT consensus blockchain for swarm
// command authenticity. Each swarm command is recorded as a Block; consensus rounds
// use a simplified PBFT (Practical Byzantine Fault Tolerance) protocol.
package swarmchain

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"
)

// PhaseMarker identifies this module in the SDACS phase registry.
const PhaseMarker = 523

// MaxByzantineNodes is the maximum fraction of faulty nodes PBFT can tolerate.
// PBFT requires n >= 3f+1 nodes for f Byzantine failures.
const MaxByzantineNodeFraction = 3

// --- Block structure ---

// BlockHeader contains metadata for a chain block.
type BlockHeader struct {
	Index      uint64    `json:"index"`
	Timestamp  time.Time `json:"timestamp"`
	PrevHash   string    `json:"prev_hash"`
	MerkleRoot string    `json:"merkle_root"`
}

// SwarmCommand is the payload stored inside each Block.
type SwarmCommand struct {
	DroneID   string `json:"drone_id"`
	CommandID string `json:"command_id"`
	Action    string `json:"action"`
	Params    string `json:"params"`
	IssuedBy  string `json:"issued_by"`
}

// Block represents a single entry in the swarm command blockchain.
type Block struct {
	Header   BlockHeader    `json:"header"`
	Commands []SwarmCommand `json:"commands"`
	Hash     string         `json:"hash"`
	Nonce    uint64         `json:"nonce"`
}

// computeHash calculates the sha256 hash of a Block's canonical JSON representation.
func computeHash(b *Block) string {
	data := fmt.Sprintf("%d|%s|%s|%s|%d",
		b.Header.Index,
		b.Header.Timestamp.UTC().Format(time.RFC3339Nano),
		b.Header.PrevHash,
		b.Header.MerkleRoot,
		b.Nonce,
	)
	sum := sha256.Sum256([]byte(data))
	return hex.EncodeToString(sum[:])
}

// merkleRoot computes the Merkle root of command IDs via iterative sha256 pairing.
func merkleRoot(cmds []SwarmCommand) string {
	if len(cmds) == 0 {
		return strings.Repeat("0", 64)
	}
	leaves := make([]string, len(cmds))
	for i, c := range cmds {
		sum := sha256.Sum256([]byte(c.CommandID + c.Action))
		leaves[i] = hex.EncodeToString(sum[:])
	}
	for len(leaves) > 1 {
		var next []string
		for i := 0; i < len(leaves); i += 2 {
			if i+1 < len(leaves) {
				combined := sha256.Sum256([]byte(leaves[i] + leaves[i+1]))
				next = append(next, hex.EncodeToString(combined[:]))
			} else {
				next = append(next, leaves[i])
			}
		}
		leaves = next
	}
	return leaves[0]
}

// NewBlock creates a new Block with computed hash.
func NewBlock(index uint64, prevHash string, cmds []SwarmCommand) *Block {
	b := &Block{
		Header: BlockHeader{
			Index:      index,
			Timestamp:  time.Now().UTC(),
			PrevHash:   prevHash,
			MerkleRoot: merkleRoot(cmds),
		},
		Commands: cmds,
	}
	b.Hash = computeHash(b)
	return b
}

// --- Blockchain ---

// Chain is a thread-safe append-only ledger of swarm command blocks.
type Chain struct {
	mu     sync.RWMutex
	blocks []*Block
}

// NewChain initialises a Chain with a genesis block.
func NewChain() *Chain {
	genesis := NewBlock(0, strings.Repeat("0", 64), nil)
	return &Chain{blocks: []*Block{genesis}}
}

// Append validates and appends a block; returns error if hash or linkage is invalid.
func (c *Chain) Append(b *Block) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	tip := c.blocks[len(c.blocks)-1]
	if b.Header.PrevHash != tip.Hash {
		return errors.New("swarmchain: block prevHash mismatch")
	}
	expected := computeHash(b)
	if b.Hash != expected {
		return fmt.Errorf("swarmchain: invalid block hash %s != %s", b.Hash, expected)
	}
	c.blocks = append(c.blocks, b)
	return nil
}

// Tip returns the most recent block.
func (c *Chain) Tip() *Block {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.blocks[len(c.blocks)-1]
}

// Len returns the number of blocks including genesis.
func (c *Chain) Len() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.blocks)
}

// --- PBFT consensus simulation ---

// PBFTMessage types follow the standard three-phase PBFT protocol.
type PBFTPhase string

const (
	PhasePrePrepare PBFTPhase = "PRE-PREPARE"
	PhasePrepare    PBFTPhase = "PREPARE"
	PhaseCommit     PBFTPhase = "COMMIT"
)

// PBFTMessage is exchanged between replica nodes during consensus.
type PBFTMessage struct {
	Phase    PBFTPhase `json:"phase"`
	View     uint64    `json:"view"`
	SeqNum   uint64    `json:"seq"`
	Digest   string    `json:"digest"` // sha256 hash of the proposed block
	NodeID   string    `json:"node_id"`
}

// PBFTNode simulates a single PBFT replica.
type PBFTNode struct {
	ID       string
	isPrimary bool
	prepares map[string]int // digest -> prepare count
	commits  map[string]int // digest -> commit count
	quorum   int
}

// NewPBFTNode creates a replica with quorum = ceil(2n/3).
func NewPBFTNode(id string, totalNodes int, isPrimary bool) *PBFTNode {
	return &PBFTNode{
		ID:        id,
		isPrimary: isPrimary,
		prepares:  make(map[string]int),
		commits:   make(map[string]int),
		quorum:    (2*totalNodes)/MaxByzantineNodeFraction + 1,
	}
}

// HandleMessage processes an incoming PBFT message and returns a response (if any).
func (n *PBFTNode) HandleMessage(msg PBFTMessage) (*PBFTMessage, bool) {
	switch msg.Phase {
	case PhasePrePrepare:
		// Replica accepts pre-prepare from primary and broadcasts PREPARE
		resp := &PBFTMessage{
			Phase: PhasePrepare, View: msg.View,
			SeqNum: msg.SeqNum, Digest: msg.Digest, NodeID: n.ID,
		}
		return resp, true
	case PhasePrepare:
		n.prepares[msg.Digest]++
		if n.prepares[msg.Digest] >= n.quorum {
			resp := &PBFTMessage{
				Phase: PhaseCommit, View: msg.View,
				SeqNum: msg.SeqNum, Digest: msg.Digest, NodeID: n.ID,
			}
			return resp, true
		}
	case PhaseCommit:
		n.commits[msg.Digest]++
		if n.commits[msg.Digest] >= n.quorum {
			return nil, true // consensus reached — block can be committed
		}
	}
	return nil, false
}

// digestBlock returns the sha256 digest of a block's JSON representation.
func digestBlock(b *Block) (string, error) {
	data, err := json.Marshal(b)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:]), nil
}

// RunConsensusRound simulates one PBFT round over a list of nodes for a proposed block.
// Returns true if quorum reached within the simulated round.
func RunConsensusRound(nodes []*PBFTNode, proposed *Block, view uint64) (bool, error) {
	digest, err := digestBlock(proposed)
	if err != nil {
		return false, err
	}
	seq := proposed.Header.Index
	// Primary broadcasts PRE-PREPARE
	prePrepare := PBFTMessage{Phase: PhasePrePrepare, View: view, SeqNum: seq, Digest: digest, NodeID: "primary"}
	var prepareMessages []PBFTMessage
	for _, node := range nodes {
		if resp, ok := node.HandleMessage(prePrepare); ok && resp != nil {
			prepareMessages = append(prepareMessages, *resp)
		}
	}
	// Distribute PREPARE messages
	commitCount := 0
	for _, pm := range prepareMessages {
		for _, node := range nodes {
			if resp, ok := node.HandleMessage(pm); ok && resp != nil {
				// Distribute COMMIT
				for _, cn := range nodes {
					_, reached := cn.HandleMessage(*resp)
					if reached && resp.Phase == PhaseCommit {
						commitCount++
					}
				}
			}
		}
	}
	return commitCount >= nodes[0].quorum, nil
}

// BlockSummary returns a human-readable summary string for a block.
func BlockSummary(b *Block) string {
	return fmt.Sprintf("Block[%d] hash=%s cmds=%d",
		b.Header.Index, b.Hash[:8]+"...", len(b.Commands))
}

// VerifyChain validates every block linkage and hash in the chain.
func VerifyChain(c *Chain) error {
	c.mu.RLock()
	defer c.mu.RUnlock()
	for i := 1; i < len(c.blocks); i++ {
		prev := c.blocks[i-1]
		cur := c.blocks[i]
		if cur.Header.PrevHash != prev.Hash {
			return fmt.Errorf("chain broken at index %d", i)
		}
		if computeHash(cur) != cur.Hash {
			return fmt.Errorf("hash mismatch at index %d", i)
		}
	}
	return nil
}

// phaseID returns the string form of the phase marker (for logging).
func phaseID() string { return "phase-" + strconv.Itoa(PhaseMarker) }

var _ = phaseID // suppress unused warning in stub
