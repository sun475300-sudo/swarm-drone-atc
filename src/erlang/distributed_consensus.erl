%% P638: Distributed Consensus - Erlang stub
%% Raft-based consensus for distributed drone coordination

-module(distributed_consensus).
-export([start/1, propose/2, get_state/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2]).

-record(state, {
    node_id :: atom(),
    role = follower :: follower | candidate | leader,
    term = 0 :: non_neg_integer(),
    log = [] :: list(),
    commit_index = 0 :: non_neg_integer()
}).

start(NodeId) ->
    gen_server:start_link({local, NodeId}, ?MODULE, [NodeId], []).

propose(Pid, Value) ->
    gen_server:call(Pid, {propose, Value}).

get_state(Pid) ->
    gen_server:call(Pid, get_state).

init([NodeId]) ->
    {ok, #state{node_id = NodeId}}.

handle_call({propose, Value}, _From, #state{role = leader} = State) ->
    NewLog = State#state.log ++ [{State#state.term, Value}],
    {reply, {ok, length(NewLog)}, State#state{log = NewLog}};
handle_call({propose, _}, _From, State) ->
    {reply, {error, not_leader}, State};
handle_call(get_state, _From, State) ->
    Reply = #{role => State#state.role, term => State#state.term,
              log_length => length(State#state.log)},
    {reply, Reply, State}.

handle_cast(_Msg, State) -> {noreply, State}.
handle_info(_Info, State) -> {noreply, State}.
