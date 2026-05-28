/**
 * Phase 310: TypeScript Blockchain Audit Trail
 * Type-safe immutable audit chain with generics,
 * discriminated unions, and async mining.
 */

import * as crypto from "crypto";

// ── Types ──────────────────────────────────────────────────────────
type EventType = "command" | "state_change" | "alert" | "decision" | "config_change";

interface AuditEvent {
  eventType: EventType;
  actor: string;
  description: string;
  data: Record<string, unknown>;
  timestamp: number;
}

interface Block {
  index: number;
  timestamp: number;
  data: AuditEvent | { type: "genesis" };
  previousHash: string;
  nonce: number;
  hash: string;
}

type ChainValidation =
  | { valid: true }
  | { valid: false; error: string; blockIndex: number };

// ── Hash Computation ───────────────────────────────────────────────
function computeHash(block: Omit<Block, "hash">): string {
  const content = JSON.stringify({
    index: block.index,
    timestamp: block.timestamp,
    data: block.data,
    previousHash: block.previousHash,
    nonce: block.nonce,
  });
  return crypto.createHash("sha256").update(content).digest("hex");
}

// ── Mining ─────────────────────────────────────────────────────────
function mineBlock(block: Omit<Block, "hash">, difficulty: number): Block {
  const target = "0".repeat(difficulty);
  let nonce = 0;
  while (true) {
    const candidate = { ...block, nonce };
    const hash = computeHash(candidate);
    if (hash.startsWith(target)) {
      return { ...candidate, hash };
    }
    nonce++;
  }
}

// ── Blockchain Audit Trail ─────────────────────────────────────────
class BlockchainAuditTrail {
  private chain: Block[] = [];
  private readonly difficulty: number;
  private pendingEvents: AuditEvent[] = [];

  constructor(difficulty: number = 2) {
    this.difficulty = difficulty;
    this.createGenesis();
  }

  private createGenesis(): void {
    const genesis: Omit<Block, "hash"> = {
      index: 0,
      timestamp: Date.now() / 1000,
      data: { type: "genesis" },
      previousHash: "0".repeat(64),
      nonce: 0,
    };
    const hash = computeHash(genesis);
    this.chain.push({ ...genesis, hash });
  }

  recordEvent(event: AuditEvent): string {
    if (event.timestamp === 0) {
      event = { ...event, timestamp: Date.now() / 1000 };
    }
    this.pendingEvents.push(event);

    const prev = this.chain[this.chain.length - 1];
    const blockData: Omit<Block, "hash"> = {
      index: this.chain.length,
      timestamp: Date.now() / 1000,
      data: event,
      previousHash: prev.hash,
      nonce: 0,
    };

    const mined = mineBlock(blockData, this.difficulty);
    this.chain.push(mined);
    return mined.hash;
  }

  verifyChain(): ChainValidation {
    for (let i = 1; i < this.chain.length; i++) {
      const current = this.chain[i];
      const previous = this.chain[i - 1];

      const recomputed = computeHash({
        index: current.index,
        timestamp: current.timestamp,
        data: current.data,
        previousHash: current.previousHash,
        nonce: current.nonce,
      });

      if (recomputed !== current.hash) {
        return { valid: false, error: "Hash mismatch", blockIndex: i };
      }
      if (current.previousHash !== previous.hash) {
        return { valid: false, error: "Previous hash mismatch", blockIndex: i };
      }
    }
    return { valid: true };
  }

  queryByType(eventType: EventType): Block[] {
    return this.chain.filter((b) => {
      const data = b.data as AuditEvent;
      return data.eventType === eventType;
    });
  }

  queryByActor(actor: string): Block[] {
    return this.chain.filter((b) => {
      const data = b.data as AuditEvent;
      return data.actor === actor;
    });
  }

  queryByTimeRange(start: number, end: number): Block[] {
    return this.chain.filter((b) => b.timestamp >= start && b.timestamp <= end);
  }

  get chainLength(): number {
    return this.chain.length;
  }

  getBlock(index: number): Block | undefined {
    return this.chain[index];
  }

  getLatestBlock(): Block {
    return this.chain[this.chain.length - 1];
  }

  exportChain(): Block[] {
    return [...this.chain];
  }

  summary(): Record<string, unknown> {
    const eventCounts: Record<string, number> = {};
    for (const block of this.chain.slice(1)) {
      const data = block.data as AuditEvent;
      if (data.eventType) {
        eventCounts[data.eventType] = (eventCounts[data.eventType] || 0) + 1;
      }
    }
    const validation = this.verifyChain();
    return {
      chainLength: this.chain.length,
      isValid: validation.valid,
      eventCounts,
      latestHash: this.getLatestBlock().hash.substring(0, 16) + "...",
      pendingEvents: this.pendingEvents.length,
    };
  }
}

// ── Main ───────────────────────────────────────────────────────────
function main(): void {
  const trail = new BlockchainAuditTrail(2);

  trail.recordEvent({
    eventType: "command",
    actor: "atc_1",
    description: "Clear drone_1 for takeoff",
    data: { drone: "drone_1" },
    timestamp: 0,
  });

  trail.recordEvent({
    eventType: "alert",
    actor: "system",
    description: "Collision warning detected",
    data: { severity: "critical" },
    timestamp: 0,
  });

  trail.recordEvent({
    eventType: "decision",
    actor: "ai_engine",
    description: "Reroute drone_3 to avoid conflict",
    data: {},
    timestamp: 0,
  });

  console.log("Summary:", JSON.stringify(trail.summary(), null, 2));
  console.log("Verification:", trail.verifyChain());
  console.log("Alerts:", trail.queryByType("alert").length);
}

main();

export { BlockchainAuditTrail, AuditEvent, Block, EventType };
