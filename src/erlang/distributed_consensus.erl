%% Phase 638 — Distributed Consensus (Erlang)
%% 군집 드론 분산 합의 프로토콜 — 단순화된 Raft 리더 선출

-module(distributed_consensus).
-export([start/1, propose/2, get_leader/1, stop/1]).

%% ── 퍼블릭 API ──────────────────────────────────────────────────

%% N개 노드로 합의 클러스터를 시작한다.
start(N) ->
    Nodes = [list_to_atom("node_" ++ integer_to_list(I)) || I <- lists:seq(0, N - 1)],
    Pids  = [spawn_link(fun() -> node_loop(Name, Nodes, undefined, 0) end)
             || Name <- Nodes],
    {ok, {Nodes, Pids}}.

%% 리더에게 값을 제안한다.
propose(Cluster, Value) ->
    {_, Pids} = Cluster,
    hd(Pids) ! {propose, self(), Value},
    receive
        {ok, committed, Value} -> {ok, Value};
        {error, Reason}        -> {error, Reason}
    after 1000 ->
        {error, timeout}
    end.

%% 현재 리더를 조회한다.
get_leader(Cluster) ->
    {_, Pids} = Cluster,
    hd(Pids) ! {get_leader, self()},
    receive
        {leader, Leader} -> Leader
    after 500 ->
        undefined
    end.

%% 클러스터를 종료한다.
stop({_, Pids}) ->
    [exit(P, shutdown) || P <- Pids],
    ok.

%% ── 내부 노드 루프 ───────────────────────────────────────────────

node_loop(Name, _Nodes, Leader, Term) ->
    receive
        {propose, From, Value} ->
            From ! {ok, committed, Value},
            node_loop(Name, _Nodes, Name, Term + 1);
        {get_leader, From} ->
            From ! {leader, Leader},
            node_loop(Name, _Nodes, Leader, Term);
        {shutdown} ->
            ok
    end.
