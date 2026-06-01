%% Distributed consensus stub for SDACS cluster coordination — Erlang
-module(distributed_consensus).
-export([start/0, propose/2, commit/2]).

start() ->
    io:format("Consensus module started~n").

propose(Node, Value) ->
    {ok, Node, Value}.

commit(Node, Value) ->
    io:format("Committed ~p on ~p~n", [Value, Node]),
    ok.
