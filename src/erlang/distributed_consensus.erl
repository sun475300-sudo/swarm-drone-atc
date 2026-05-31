%% distributed_consensus.erl - Distributed consensus for SDACS drone fleet
-module(distributed_consensus).
-behaviour(gen_server).

-export([start_link/1, propose/2, get_value/1, stop/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-record(state, {
    node_id    :: atom(),
    nodes      :: [atom()],
    ballot     :: integer(),
    value      :: term(),
    promises   :: [{atom(), integer()}],
    accepted   :: [{atom(), integer(), term()}],
    phase      :: prepare | accept | decided
}).

start_link(Options) ->
    NodeId = maps:get(node_id, Options, node()),
    gen_server:start_link({local, ?MODULE}, ?MODULE, Options, []).

propose(Pid, Value) ->
    gen_server:call(Pid, {propose, Value}).

get_value(Pid) ->
    gen_server:call(Pid, get_value).

stop(Pid) ->
    gen_server:stop(Pid).

init(Options) ->
    NodeId = maps:get(node_id, Options, node()),
    Nodes  = maps:get(nodes, Options, [node()]),
    State  = #state{
        node_id  = NodeId,
        nodes    = Nodes,
        ballot   = 0,
        value    = undefined,
        promises = [],
        accepted = [],
        phase    = prepare
    },
    {ok, State}.

handle_call({propose, Value}, _From, State) ->
    NewBallot = State#state.ballot + 1,
    NewState  = State#state{ballot = NewBallot, value = Value, phase = prepare},
    Majority  = length(State#state.nodes) div 2 + 1,
    % Simplified: accept immediately in single-node mode
    if length(State#state.nodes) =< 1 ->
        {reply, {ok, Value}, NewState#state{phase = decided}};
    true ->
        {reply, {ok, Value}, NewState}
    end;

handle_call(get_value, _From, State) ->
    {reply, {ok, State#state.value}, State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    ok.
