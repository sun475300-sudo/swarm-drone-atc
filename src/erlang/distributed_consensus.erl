-module(distributed_consensus).
-export([start/0, propose/2, decide/1]).
start() -> ok.
propose(Node, Value) -> {Node, Value}.
decide(Proposals) -> hd(Proposals).
drone(Id) -> {consensus, Id}.
