/// Phase 321: Zig PBFT Consensus Engine
/// Byzantine Fault Tolerant consensus with zero-allocation message passing.
/// Supports 3f+1 nodes with view change protocol.

const std = @import("std");

pub const NodeRole = enum {
    primary,
    backup,
    faulty,
};

pub const MessageType = enum {
    pre_prepare,
    prepare,
    commit,
    reply,
    view_change,
};

pub const PBFTMessage = struct {
    msg_type: MessageType,
    view: u32,
    sequence: u32,
    sender: u32,
    digest: [16]u8,
    timestamp: f64,
};

pub const PBFTNode = struct {
    node_id: u32,
    role: NodeRole,
    view: u32,
    committed_count: u32 = 0,
    is_faulty: bool = false,
};

pub const ConsensusResult = struct {
    committed: bool,
    sequence: u32,
    view: u32,
    prepare_count: u32,
    commit_count: u32,
};

pub const PBFTEngine = struct {
    nodes: [16]PBFTNode = undefined,
    n_nodes: u32,
    f_faulty: u32,
    current_view: u32 = 0,
    sequence: u32 = 0,
    committed_ops: u32 = 0,
    message_count: u64 = 0,

    pub fn init(n_nodes: u32, f_faulty: u32) PBFTEngine {
        var engine = PBFTEngine{
            .n_nodes = n_nodes,
            .f_faulty = f_faulty,
        };
        for (0..n_nodes) |i| {
            engine.nodes[i] = PBFTNode{
                .node_id = @intCast(i),
                .role = if (i == 0) .primary else .backup,
                .view = 0,
            };
        }
        return engine;
    }

    pub fn setFaulty(self: *PBFTEngine, node_id: u32) void {
        if (node_id < self.n_nodes) {
            self.nodes[node_id].is_faulty = true;
            self.nodes[node_id].role = .faulty;
        }
    }

    pub fn submitRequest(self: *PBFTEngine) ConsensusResult {
        self.sequence += 1;
        const seq = self.sequence;
        const primary_id = self.current_view % self.n_nodes;

        // Check primary is not faulty
        if (self.nodes[primary_id].is_faulty) {
            return ConsensusResult{
                .committed = false,
                .sequence = seq,
                .view = self.current_view,
                .prepare_count = 0,
                .commit_count = 0,
            };
        }

        // Count prepares from non-faulty backups
        var prepare_count: u32 = 0;
        for (0..self.n_nodes) |i| {
            if (i != primary_id and !self.nodes[i].is_faulty) {
                prepare_count += 1;
                self.message_count += 1;
            }
        }

        // Count commits from all non-faulty nodes
        var commit_count: u32 = 0;
        for (0..self.n_nodes) |i| {
            if (!self.nodes[i].is_faulty) {
                commit_count += 1;
                self.message_count += 1;
            }
        }

        const quorum_prepare = 2 * self.f_faulty;
        const quorum_commit = 2 * self.f_faulty + 1;
        const committed = prepare_count >= quorum_prepare and commit_count >= quorum_commit;

        if (committed) {
            self.committed_ops += 1;
            for (0..self.n_nodes) |i| {
                if (!self.nodes[i].is_faulty) {
                    self.nodes[i].committed_count += 1;
                }
            }
        }

        return ConsensusResult{
            .committed = committed,
            .sequence = seq,
            .view = self.current_view,
            .prepare_count = prepare_count,
            .commit_count = commit_count,
        };
    }

    pub fn viewChange(self: *PBFTEngine) u32 {
        self.current_view += 1;
        const new_primary = self.current_view % self.n_nodes;
        for (0..self.n_nodes) |i| {
            self.nodes[i].view = self.current_view;
            if (i == new_primary and !self.nodes[i].is_faulty) {
                self.nodes[i].role = .primary;
            } else if (!self.nodes[i].is_faulty) {
                self.nodes[i].role = .backup;
            }
        }
        return self.current_view;
    }

    pub fn verifyConsistency(self: *const PBFTEngine) bool {
        var first_count: ?u32 = null;
        for (0..self.n_nodes) |i| {
            if (!self.nodes[i].is_faulty) {
                if (first_count) |fc| {
                    if (self.nodes[i].committed_count != fc) return false;
                } else {
                    first_count = self.nodes[i].committed_count;
                }
            }
        }
        return true;
    }
};

// ── Tests ──────────────────────────────────────────────────────
test "PBFT basic consensus" {
    var engine = PBFTEngine.init(4, 1);
    const result = engine.submitRequest();
    try std.testing.expect(result.committed);
    try std.testing.expectEqual(engine.committed_ops, 1);
}

test "PBFT with faulty node" {
    var engine = PBFTEngine.init(7, 2);
    engine.setFaulty(1);
    engine.setFaulty(2);
    const result = engine.submitRequest();
    try std.testing.expect(result.committed);
}

test "PBFT consistency" {
    var engine = PBFTEngine.init(4, 1);
    _ = engine.submitRequest();
    _ = engine.submitRequest();
    try std.testing.expect(engine.verifyConsistency());
}

test "PBFT view change" {
    var engine = PBFTEngine.init(4, 1);
    const new_view = engine.viewChange();
    try std.testing.expectEqual(new_view, 1);
    try std.testing.expectEqual(engine.nodes[1].role, .primary);
}
