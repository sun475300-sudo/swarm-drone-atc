// Phase 343: Go Sovereignty Router
// Data sovereignty routing with region-based policies.
// Goroutine-safe region enforcement.

package main

import (
	"crypto/sha256"
	"fmt"
	"strings"
	"sync"
	"time"
)

// ── Types ────────────────────────────────────────────────────────

type Region string

const (
	RegionKR     Region = "kr"
	RegionUS     Region = "us"
	RegionEU     Region = "eu"
	RegionJP     Region = "jp"
	RegionGlobal Region = "global"
)

type Classification string

const (
	Public       Classification = "public"
	Internal     Classification = "internal"
	Confidential Classification = "confidential"
	Restricted   Classification = "restricted"
)

type EncryptionLevel string

const (
	EncNone   EncryptionLevel = "none"
	EncAES128 EncryptionLevel = "aes128"
	EncAES256 EncryptionLevel = "aes256"
)

type DataPolicy struct {
	Classification Classification
	AllowedRegions map[Region]bool
	Encryption     EncryptionLevel
	RetentionDays  int
	RequiresAnon   bool
}

type DataRecord struct {
	RecordID       string
	SourceRegion   Region
	Classification Classification
	PayloadHash    string
	SizeBytes      int
	Timestamp      time.Time
	RoutedTo       Region
	Encrypted      bool
}

type RouteDecision struct {
	RecordID string
	Target   Region
	Allowed  bool
	Reason   string
}

type AuditEntry struct {
	Action    string
	RecordID  string
	From      Region
	To        Region
	Compliant bool
	Timestamp time.Time
}

// ── Sovereignty Router ──────────────────────────────────────────

type SovereigntyRouter struct {
	mu         sync.RWMutex
	homeRegion Region
	policies   map[Classification]*DataPolicy
	records    map[string]*DataRecord
	audit      []AuditEntry
	violations int
}

func NewSovereigntyRouter(home Region) *SovereigntyRouter {
	r := &SovereigntyRouter{
		homeRegion: home,
		policies:   make(map[Classification]*DataPolicy),
		records:    make(map[string]*DataRecord),
	}
	// Default policies
	r.policies[Public] = &DataPolicy{
		Classification: Public,
		AllowedRegions: map[Region]bool{RegionGlobal: true},
		Encryption:     EncNone,
		RetentionDays:  365,
	}
	r.policies[Internal] = &DataPolicy{
		Classification: Internal,
		AllowedRegions: map[Region]bool{RegionKR: true, RegionUS: true, RegionEU: true, RegionJP: true},
		Encryption:     EncAES128,
		RetentionDays:  180,
	}
	r.policies[Confidential] = &DataPolicy{
		Classification: Confidential,
		AllowedRegions: map[Region]bool{RegionKR: true},
		Encryption:     EncAES256,
		RetentionDays:  90,
		RequiresAnon:   true,
	}
	r.policies[Restricted] = &DataPolicy{
		Classification: Restricted,
		AllowedRegions: map[Region]bool{RegionKR: true},
		Encryption:     EncAES256,
		RetentionDays:  30,
		RequiresAnon:   true,
	}
	return r
}

func (r *SovereigntyRouter) Ingest(id string, source Region, cls Classification, payload []byte) *DataRecord {
	r.mu.Lock()
	defer r.mu.Unlock()

	hash := sha256.Sum256(payload)
	policy := r.policies[cls]
	encrypted := policy != nil && policy.Encryption != EncNone

	rec := &DataRecord{
		RecordID:       id,
		SourceRegion:   source,
		Classification: cls,
		PayloadHash:    fmt.Sprintf("%x", hash[:8]),
		SizeBytes:      len(payload),
		Timestamp:      time.Now(),
		Encrypted:      encrypted,
	}
	r.records[id] = rec

	r.audit = append(r.audit, AuditEntry{
		Action: "ingest", RecordID: id,
		From: source, Compliant: true,
		Timestamp: time.Now(),
	})
	return rec
}

func (r *SovereigntyRouter) Route(id string, target Region) RouteDecision {
	r.mu.Lock()
	defer r.mu.Unlock()

	rec, ok := r.records[id]
	if !ok {
		return RouteDecision{RecordID: id, Target: target, Allowed: false, Reason: "not found"}
	}

	policy := r.policies[rec.Classification]
	if policy == nil {
		return RouteDecision{RecordID: id, Target: target, Allowed: false, Reason: "no policy"}
	}

	// Check region
	if !policy.AllowedRegions[RegionGlobal] && !policy.AllowedRegions[target] {
		r.violations++
		r.audit = append(r.audit, AuditEntry{
			Action: "route_denied", RecordID: id,
			From: rec.SourceRegion, To: target,
			Compliant: false, Timestamp: time.Now(),
		})
		return RouteDecision{
			RecordID: id, Target: target, Allowed: false,
			Reason: fmt.Sprintf("region %s not allowed for %s", target, rec.Classification),
		}
	}

	rec.RoutedTo = target
	r.audit = append(r.audit, AuditEntry{
		Action: "route", RecordID: id,
		From: rec.SourceRegion, To: target,
		Compliant: true, Timestamp: time.Now(),
	})
	return RouteDecision{RecordID: id, Target: target, Allowed: true}
}

func (r *SovereigntyRouter) BulkRoute(ids []string, target Region) []RouteDecision {
	decisions := make([]RouteDecision, 0, len(ids))
	for _, id := range ids {
		decisions = append(decisions, r.Route(id, target))
	}
	return decisions
}

type RouterStats struct {
	TotalRecords int
	Violations   int
	AuditEntries int
	RegionDist   map[Region]int
}

func (r *SovereigntyRouter) Stats() RouterStats {
	r.mu.RLock()
	defer r.mu.RUnlock()

	dist := make(map[Region]int)
	for _, rec := range r.records {
		region := rec.SourceRegion
		if rec.RoutedTo != "" {
			region = rec.RoutedTo
		}
		dist[region]++
	}

	return RouterStats{
		TotalRecords: len(r.records),
		Violations:   r.violations,
		AuditEntries: len(r.audit),
		RegionDist:   dist,
	}
}

func main() {
	router := NewSovereigntyRouter(RegionKR)

	// Ingest test data
	for i := 0; i < 10; i++ {
		cls := []Classification{Public, Internal, Confidential}[i%3]
		router.Ingest(fmt.Sprintf("rec_%d", i), RegionKR, cls, []byte(fmt.Sprintf("data_%d", i)))
	}

	// Route tests
	d1 := router.Route("rec_0", RegionUS) // public → allowed
	d2 := router.Route("rec_2", RegionUS) // confidential → blocked

	fmt.Printf("Public→US: allowed=%v\n", d1.Allowed)
	fmt.Printf("Confidential→US: allowed=%v (%s)\n", d2.Allowed, d2.Reason)

	stats := router.Stats()
	fmt.Printf("Records: %d | Violations: %d | Audit: %d\n",
		stats.TotalRecords, stats.Violations, stats.AuditEntries)

	_ = strings.Join(nil, "") // suppress unused import
}
