%% Phase 638: Distributed Consensus — Erlang
%% SDACS Raft consensus implementation for distributed drone coordination

-module(distributed_consensus).
-behaviour(gen_server).

-export([start_link/1, propose/2, get_state/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-record(raft_state, {
    node_id      :: atom(),
    role         :: leader | follower | candidate,
    term         :: non_neg_integer(),
    voted_for    :: atom() | undefined,
    log          :: list(),
    commit_index :: non_neg_integer(),
    peers        :: list(atom())
}).

start_link(NodeId) ->
    gen_server:start_link({local, NodeId}, ?MODULE, [NodeId], []).

propose(NodeId, Command) ->
    gen_server:call(NodeId, {propose, Command}).

get_state(NodeId) ->
    gen_server:call(NodeId, get_state).

init([NodeId]) ->
    State = #raft_state{
        node_id      = NodeId,
        role         = follower,
        term         = 0,
        voted_for    = undefined,
        log          = [],
        commit_index = 0,
        peers        = []
    },
    {ok, State}.

handle_call({propose, Command}, _From, #raft_state{role = leader} = State) ->
    NewLog = State#raft_state.log ++ [{State#raft_state.term, Command}],
    {reply, {ok, length(NewLog)}, State#raft_state{log = NewLog}};
handle_call({propose, _}, _From, State) ->
    {reply, {error, not_leader}, State};
handle_call(get_state, _From, State) ->
    {reply, {State#raft_state.role, State#raft_state.term, length(State#raft_state.log)}, State}.

handle_cast({vote_request, Term, CandidateId}, State) when Term > State#raft_state.term ->
    gen_server:cast(CandidateId, {vote_granted, State#raft_state.node_id}),
    {noreply, State#raft_state{term = Term, voted_for = CandidateId, role = follower}};
handle_cast(_, State) ->
    {noreply, State}.

handle_info(_, State) -> {noreply, State}.
terminate(_, _) -> ok.
