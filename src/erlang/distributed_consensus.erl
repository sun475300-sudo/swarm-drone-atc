% Phase 638 — Erlang Raft Distributed Consensus for SDACS Swarm
-module(raft_consensus).
-export([start/1, vote/2, append_entries/3]).

-record(state, {role=follower, term=0, voted_for=undefined, log=[], commit_index=0}).

start(NodeId) ->
    spawn(fun() -> loop(#state{}, NodeId) end).

loop(State, NodeId) ->
    receive
        {request_vote, Term, CandidateId, From} ->
            {Reply, NewState} = handle_vote(State, Term, CandidateId),
            From ! {vote_reply, Reply},
            loop(NewState, NodeId);
        {append_entries, Term, LeaderId, Entries, From} ->
            NewState = handle_append(State, Term, LeaderId, Entries),
            From ! {append_reply, true},
            loop(NewState, NodeId)
    after 150 -> loop(State#state{role=candidate}, NodeId)
    end.

handle_vote(S=#state{term=T}, Term, Candidate) when Term > T ->
    {granted, S#state{term=Term, voted_for=Candidate, role=follower}};
handle_vote(S, _Term, _Candidate) -> {denied, S}.

handle_append(S=#state{term=T}, Term, _Leader, Entries) when Term >= T ->
    S#state{term=Term, log=S#state.log ++ Entries, role=follower};
handle_append(S, _Term, _Leader, _Entries) -> S.

vote(Pid, CandidateId) -> Pid ! {request_vote, 1, CandidateId, self()}.
append_entries(Pid, LeaderId, Entries) -> Pid ! {append_entries, 1, LeaderId, Entries, self()}.
