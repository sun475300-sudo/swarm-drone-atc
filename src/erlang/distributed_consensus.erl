%% Phase 638 — Erlang Raft Distributed Consensus for SDACS
%% Simplified Raft leader election and log replication skeleton
-module(distributed_consensus).
-export([start/1, propose/2, stop/1]).

-record(state, {
    id        :: atom(),
    role      :: follower | candidate | leader,
    term      :: non_neg_integer(),
    log       :: list(),
    peers     :: [pid()]
}).

%% Start a consensus node.
-spec start(atom()) -> pid().
start(Id) ->
    spawn(fun() -> loop(#state{id=Id, role=follower, term=0, log=[], peers=[]}) end).

%% Propose a new log entry (leader only).
-spec propose(pid(), term()) -> ok | not_leader.
propose(Node, Entry) ->
    Node ! {propose, self(), Entry},
    receive
        {ok, _Index} -> ok;
        not_leader   -> not_leader
    after 1000 -> timeout
    end.

%% Stop the node.
stop(Node) -> Node ! stop.

%% Internal message loop.
loop(#state{role=leader}=S) ->
    receive
        {propose, From, Entry} ->
            NewLog = S#state.log ++ [Entry],
            From ! {ok, length(NewLog)},
            loop(S#state{log=NewLog});
        stop -> ok
    end;
loop(S) ->
    receive
        {propose, From, _Entry} ->
            From ! not_leader,
            loop(S);
        {elect, _Term} ->
            loop(S#state{role=leader});
        stop -> ok
    end.
