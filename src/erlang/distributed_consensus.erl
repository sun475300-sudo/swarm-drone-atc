%% Phase 638 — Raft Distributed Consensus in Erlang
-module(distributed_consensus).
-behaviour(gen_server).
-export([start_link/1, propose/2, get_state/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2]).

-record(state, {node_id, role=follower, term=0, log=[], leader=undefined}).

start_link(NodeId) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [NodeId], []).

propose(Pid, Entry) ->
    gen_server:call(Pid, {propose, Entry}).

get_state(Pid) ->
    gen_server:call(Pid, get_state).

init([NodeId]) ->
    {ok, #state{node_id=NodeId}}.

handle_call({propose, Entry}, _From, #state{log=Log, term=Term}=S) ->
    NewLog = Log ++ [{Term, Entry}],
    {reply, {ok, length(NewLog)}, S#state{log=NewLog}};
handle_call(get_state, _From, S) ->
    {reply, S, S}.

handle_cast(_Msg, State) -> {noreply, State}.
handle_info(_Info, State) -> {noreply, State}.
