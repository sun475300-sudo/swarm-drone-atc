// Phase 293: Go Raft Consensus — 분산 합의 프로토콜 (Go 구현)
// 고루틴 기반 비동기 리더 선출 및 로그 복제.

package consensus

import (
	"fmt"
	"math/rand"
	"sync"
	"time"
)

type NodeRole int

const (
	Follower NodeRole = iota
	Candidate
	Leader
)

type LogEntry struct {
	Term  int
	Index int
	Data  map[string]interface{}
}

type RaftNode struct {
	mu          sync.RWMutex
	ID          string
	Role        NodeRole
	CurrentTerm int
	VotedFor    string
	Log         []LogEntry
	CommitIndex int
	LastApplied int
	IsAlive     bool
}

type RaftCluster struct {
	mu       sync.RWMutex
	nodes    map[string]*RaftNode
	leaderID string
	history  []map[string]interface{}
	rng      *rand.Rand
}

func NewRaftCluster() *RaftCluster {
	return &RaftCluster{
		nodes:   make(map[string]*RaftNode),
		history: make([]map[string]interface{}, 0),
		rng:     rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}

func (c *RaftCluster) AddNode(id string) *RaftNode {
	c.mu.Lock()
	defer c.mu.Unlock()
	node := &RaftNode{ID: id, Role: Follower, IsAlive: true}
	c.nodes[id] = node
	return node
}

func (c *RaftCluster) QuorumSize() int {
	return len(c.nodes)/2 + 1
}

func (c *RaftCluster) StartElection(candidateID string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()

	node, ok := c.nodes[candidateID]
	if !ok || !node.IsAlive {
		return false
	}

	node.CurrentTerm++
	node.Role = Candidate
	node.VotedFor = candidateID
	votes := 1

	for id, n := range c.nodes {
		if id == candidateID || !n.IsAlive {
			continue
		}
		if n.VotedFor == "" || n.CurrentTerm < node.CurrentTerm {
			n.VotedFor = candidateID
			n.CurrentTerm = node.CurrentTerm
			votes++
		}
	}

	if votes >= c.QuorumSize() {
		node.Role = Leader
		c.leaderID = candidateID
		for id, n := range c.nodes {
			if id != candidateID {
				n.Role = Follower
			}
		}
		c.history = append(c.history, map[string]interface{}{
			"event":  "leader_elected",
			"leader": candidateID,
			"term":   node.CurrentTerm,
		})
		return true
	}

	node.Role = Follower
	return false
}

func (c *RaftCluster) Propose(data map[string]interface{}) *LogEntry {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.leaderID == "" {
		return nil
	}
	leader, ok := c.nodes[c.leaderID]
	if !ok {
		return nil
	}

	entry := LogEntry{
		Term:  leader.CurrentTerm,
		Index: len(leader.Log),
		Data:  data,
	}
	leader.Log = append(leader.Log, entry)

	replicated := 1
	for id, node := range c.nodes {
		if id == c.leaderID || !node.IsAlive {
			continue
		}
		node.Log = append(node.Log, entry)
		replicated++
	}

	if replicated >= c.QuorumSize() {
		leader.CommitIndex = entry.Index
		return &entry
	}
	return nil
}

func (c *RaftCluster) GetLeader() string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.leaderID
}

func (c *RaftCluster) KillNode(id string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if node, ok := c.nodes[id]; ok {
		node.IsAlive = false
		if c.leaderID == id {
			c.leaderID = ""
		}
	}
}

func (c *RaftCluster) Summary() map[string]interface{} {
	c.mu.RLock()
	defer c.mu.RUnlock()
	alive := 0
	for _, n := range c.nodes {
		if n.IsAlive {
			alive++
		}
	}
	return map[string]interface{}{
		"total_nodes": len(c.nodes),
		"alive_nodes": alive,
		"leader":      c.leaderID,
		"history":     len(c.history),
	}
}

func init() {
	_ = fmt.Sprintf("SDACS Raft Consensus v1.0")
}
