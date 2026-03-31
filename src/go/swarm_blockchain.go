// Phase 523: Go Swarm Blockchain — PBFT Consensus
package main

import (
	"crypto/sha256"
	"fmt"
	"math"
	"strings"
)

type TxType int

const (
	TxRegistration TxType = iota
	TxMissionAssign
	TxStatusUpdate
	TxPenalty
)

type Transaction struct {
	TxID     string
	TxType   TxType
	Sender   string
	Receiver string
	Data     string
	Sig      string
}

type Block struct {
	Index        int
	Transactions []Transaction
	PrevHash     string
	Nonce        uint64
	Hash         string
}

func computeHash(b *Block) string {
	content := fmt.Sprintf("%d:%s:%d", b.Index, b.PrevHash, b.Nonce)
	for _, tx := range b.Transactions {
		content += tx.TxID
	}
	h := sha256.Sum256([]byte(content))
	return fmt.Sprintf("%x", h[:16])
}

type Ledger struct {
	Chain     []Block
	Pending   []Transaction
	TxCount   int
}

func NewLedger() *Ledger {
	genesis := Block{Index: 0, PrevHash: strings.Repeat("0", 32)}
	genesis.Hash = computeHash(&genesis)
	return &Ledger{Chain: []Block{genesis}}
}

func (l *Ledger) AddTx(txType TxType, sender, receiver, data string) Transaction {
	l.TxCount++
	sig := fmt.Sprintf("%x", sha256.Sum256([]byte(fmt.Sprintf("%s:%d", sender, l.TxCount))))[:16]
	tx := Transaction{
		TxID: fmt.Sprintf("TX-%06d", l.TxCount), TxType: txType,
		Sender: sender, Receiver: receiver, Data: data, Sig: sig,
	}
	l.Pending = append(l.Pending, tx)
	return tx
}

func (l *Ledger) MineBlock(nonce uint64) *Block {
	if len(l.Pending) == 0 { return nil }
	n := int(math.Min(float64(len(l.Pending)), 50))
	block := Block{
		Index: len(l.Chain), Transactions: l.Pending[:n],
		PrevHash: l.Chain[len(l.Chain)-1].Hash, Nonce: nonce,
	}
	block.Hash = computeHash(&block)
	l.Chain = append(l.Chain, block)
	l.Pending = l.Pending[n:]
	return &block
}

func (l *Ledger) Verify() bool {
	for i := 1; i < len(l.Chain); i++ {
		if l.Chain[i].PrevHash != l.Chain[i-1].Hash { return false }
		if l.Chain[i].Hash != computeHash(&l.Chain[i]) { return false }
	}
	return true
}

type PBFTNode struct {
	ID     int
	Honest bool
}

func pbftConsensus(nodes []PBFTNode, block *Block) (bool, int) {
	f := (len(nodes) - 1) / 3
	commits := 0
	for _, n := range nodes {
		if n.Honest { commits++ }
	}
	return commits >= 2*f+1, commits
}

func main() {
	ledger := NewLedger()

	for i := 0; i < 20; i++ {
		ledger.AddTx(TxRegistration, "system", fmt.Sprintf("drone_%d", i),
			fmt.Sprintf(`{"stake":%d}`, 50+i*5))
	}
	ledger.MineBlock(12345)

	for i := 0; i < 10; i++ {
		ledger.AddTx(TxStatusUpdate, fmt.Sprintf("drone_%d", i), "ledger",
			fmt.Sprintf(`{"battery":%d,"alt":%d}`, 80-i*3, 50+i*10))
	}
	block := ledger.MineBlock(67890)

	nodes := make([]PBFTNode, 10)
	for i := range nodes {
		nodes[i] = PBFTNode{ID: i, Honest: i != 7}
	}
	accepted, commits := pbftConsensus(nodes, block)

	fmt.Printf("Chain height: %d\n", len(ledger.Chain))
	fmt.Printf("Total TX: %d\n", ledger.TxCount)
	fmt.Printf("Chain valid: %v\n", ledger.Verify())
	fmt.Printf("PBFT: accepted=%v commits=%d/10\n", accepted, commits)
}
