%% SDACS Distributed Consensus — Erlang/OTP
%% 드론 군집 분산 합의 프로토콜 (Raft 기반 단순화)

-module(distributed_consensus).
-behaviour(gen_server).

-export([start_link/1, propose/2, get_state/1, add_peer/2, stop/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-record(state, {
    node_id     :: atom(),
    role        :: leader | follower | candidate,
    term        :: non_neg_integer(),
    log         :: list(),
    peers       :: list(),
    votes       :: non_neg_integer(),
    committed   :: list()
}).

%% Public API

start_link(NodeId) ->
    gen_server:start_link(?MODULE, NodeId, []).

propose(Pid, Value) ->
    gen_server:call(Pid, {propose, Value}).

get_state(Pid) ->
    gen_server:call(Pid, get_state).

add_peer(Pid, PeerPid) ->
    gen_server:call(Pid, {add_peer, PeerPid}).

stop(Pid) ->
    gen_server:stop(Pid).

%% gen_server callbacks

init(NodeId) ->
    {ok, #state{
        node_id   = NodeId,
        role      = follower,
        term      = 0,
        log       = [],
        peers     = [],
        votes     = 0,
        committed = []
    }}.

handle_call({propose, Value}, _From, #state{role = leader} = S) ->
    Entry = #{term => S#state.term, value => Value, index => length(S#state.log) + 1},
    NewLog = S#state.log ++ [Entry],
    NewCommitted = NewLog,
    broadcast_to_peers(S#state.peers, {append_entries, Entry}),
    {reply, {ok, committed}, S#state{log = NewLog, committed = NewCommitted}};

handle_call({propose, Value}, _From, S) ->
    {reply, {redirect, S#state.node_id}, S};

handle_call(get_state, _From, S) ->
    Info = #{
        node_id   => S#state.node_id,
        role      => S#state.role,
        term      => S#state.term,
        log_len   => length(S#state.log),
        committed => length(S#state.committed),
        peers     => length(S#state.peers)
    },
    {reply, Info, S};

handle_call({add_peer, Pid}, _From, S) ->
    {reply, ok, S#state{peers = [Pid | S#state.peers]}};

handle_call(become_leader, _From, S) ->
    {reply, ok, S#state{role = leader, term = S#state.term + 1}};

handle_call(_Req, _From, S) ->
    {reply, {error, unknown}, S}.

handle_cast({append_entries, Entry}, S) ->
    NewLog = S#state.log ++ [Entry],
    {noreply, S#state{log = NewLog, committed = NewLog}};

handle_cast(_Msg, S) ->
    {noreply, S}.

handle_info(_Info, S) ->
    {noreply, S}.

terminate(_Reason, _S) ->
    ok.

%% Internal helpers

broadcast_to_peers(Peers, Msg) ->
    lists:foreach(fun(P) -> gen_server:cast(P, Msg) end, Peers).
