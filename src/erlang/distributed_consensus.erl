%% Phase 638: Distributed Consensus — Erlang Raft OTP
%% Raft 합의 프로토콜 OTP 구현

-module(distributed_consensus).
-behaviour(gen_server).

-export([start_link/1, init/1, handle_call/3, handle_cast/2, handle_info/2]).
-export([request_vote/2, append_entries/2, get_state/1]).

-record(state, {
    node_id :: atom(),
    role = follower :: leader | candidate | follower,
    current_term = 0 :: non_neg_integer(),
    voted_for = undefined :: atom() | undefined,
    log = [] :: [{non_neg_integer(), term()}],
    commit_index = 0 :: non_neg_integer(),
    last_applied = 0 :: non_neg_integer(),
    peers = [] :: [atom()],
    votes_received = 0 :: non_neg_integer(),
    leader_id = undefined :: atom() | undefined
}).

%% API
start_link(NodeId) ->
    gen_server:start_link({local, NodeId}, ?MODULE, NodeId, []).

request_vote(NodeId, CandidateId) ->
    gen_server:call(NodeId, {request_vote, CandidateId}).

append_entries(NodeId, Entries) ->
    gen_server:call(NodeId, {append_entries, Entries}).

get_state(NodeId) ->
    gen_server:call(NodeId, get_state).

%% Callbacks
init(NodeId) ->
    State = #state{
        node_id = NodeId,
        role = follower,
        current_term = 0,
        log = [],
        peers = []
    },
    {ok, State}.

handle_call({request_vote, CandidateId}, _From, State) ->
    #state{current_term = Term, voted_for = VotedFor} = State,
    case VotedFor of
        undefined ->
            NewState = State#state{
                voted_for = CandidateId,
                current_term = Term + 1
            },
            {reply, {vote_granted, Term + 1}, NewState};
        CandidateId ->
            {reply, {vote_granted, Term}, State};
        _ ->
            {reply, {vote_denied, Term}, State}
    end;

handle_call({append_entries, Entries}, _From, State) ->
    #state{log = Log, current_term = Term} = State,
    NewLog = Log ++ Entries,
    NewState = State#state{
        log = NewLog,
        commit_index = length(NewLog)
    },
    {reply, {ok, Term, length(NewLog)}, NewState};

handle_call(get_state, _From, State) ->
    Summary = #{
        node_id => State#state.node_id,
        role => State#state.role,
        term => State#state.current_term,
        log_length => length(State#state.log),
        commit_index => State#state.commit_index
    },
    {reply, Summary, State}.

handle_cast({become_leader, Term}, State) ->
    NewState = State#state{role = leader, current_term = Term},
    {noreply, NewState};

handle_cast({become_follower, LeaderId}, State) ->
    NewState = State#state{role = follower, leader_id = LeaderId},
    {noreply, NewState}.

handle_info(election_timeout, State) ->
    case State#state.role of
        follower ->
            NewState = State#state{
                role = candidate,
                current_term = State#state.current_term + 1,
                votes_received = 1,
                voted_for = State#state.node_id
            },
            {noreply, NewState};
        _ ->
            {noreply, State}
    end;

handle_info(_Msg, State) ->
    {noreply, State}.
