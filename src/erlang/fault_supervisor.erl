%% Phase 575: fault_supervisor — Erlang 기반 결함 허용 감독자
%% SDACS Fault-Tolerant Supervisor for Drone Process Management

-module(fault_supervisor).
-behaviour(supervisor).

-export([start_link/0, start_link/1, init/1]).
-export([add_drone/2, remove_drone/1, get_drone_status/1, list_drones/0]).
-export([restart_drone/1, stop_all/0]).

%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%% OTP Supervisor 콜백
%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-define(SERVER, ?MODULE).
-define(MAX_RESTART, 5).
-define(MAX_TIME, 60).

start_link() ->
    start_link([]).

start_link(DroneIds) ->
    supervisor:start_link({local, ?SERVER}, ?MODULE, DroneIds).

%% supervisor 초기화 — one_for_one 재시작 전략
init(DroneIds) ->
    io:format("SDACS Fault Supervisor 초기화 — Phase 575~n"),
    SupFlags = #{
        strategy  => one_for_one,
        intensity => ?MAX_RESTART,
        period    => ?MAX_TIME
    },
    %% 드론 워커 명세 생성
    Children = lists:map(fun(DroneId) ->
        drone_child_spec(DroneId)
    end, DroneIds),
    {ok, {SupFlags, Children}}.

%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%% 드론 워커 명세
%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

drone_child_spec(DroneId) ->
    #{
        id       => {drone_worker, DroneId},
        start    => {drone_worker, start_link, [DroneId]},
        restart  => permanent,    %% 항상 재시작
        shutdown => 5000,
        type     => worker,
        modules  => [drone_worker]
    }.

%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%% 공개 API
%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

add_drone(DroneId, _Config) ->
    Spec = drone_child_spec(DroneId),
    case supervisor:start_child(?SERVER, Spec) of
        {ok, Pid} ->
            io:format("드론 ~p 추가: pid=~p~n", [DroneId, Pid]),
            {ok, DroneId};
        {error, Reason} ->
            io:format("드론 ~p 추가 실패: ~p~n", [DroneId, Reason]),
            {error, Reason}
    end.

remove_drone(DroneId) ->
    ChildId = {drone_worker, DroneId},
    case supervisor:terminate_child(?SERVER, ChildId) of
        ok ->
            supervisor:delete_child(?SERVER, ChildId),
            io:format("드론 ~p 제거 완료~n", [DroneId]),
            ok;
        {error, Reason} ->
            {error, Reason}
    end.

restart_drone(DroneId) ->
    ChildId = {drone_worker, DroneId},
    supervisor:restart_child(?SERVER, ChildId).

get_drone_status(DroneId) ->
    ChildId = {drone_worker, DroneId},
    Children = supervisor:which_children(?SERVER),
    case lists:keyfind(ChildId, 1, Children) of
        {ChildId, Pid, _Type, _Modules} when is_pid(Pid) ->
            {running, Pid};
        {ChildId, undefined, _Type, _Modules} ->
            {stopped, DroneId};
        false ->
            {not_found, DroneId}
    end.

list_drones() ->
    Children = supervisor:which_children(?SERVER),
    lists:map(fun({Id, Pid, _Type, _Mods}) ->
        Status = if is_pid(Pid) -> running; true -> stopped end,
        {Id, Status, Pid}
    end, Children).

stop_all() ->
    Children = supervisor:which_children(?SERVER),
    lists:foreach(fun({Id, _, _, _}) ->
        supervisor:terminate_child(?SERVER, Id)
    end, Children),
    io:format("모든 드론 워커 중지 완료~n").

%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%% 드론 워커 모듈 (인라인)
%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-module(drone_worker).
-export([start_link/1, init/1]).

start_link(DroneId) ->
    Pid = spawn_link(?MODULE, init, [DroneId]),
    {ok, Pid}.

init(DroneId) ->
    io:format("  드론 워커 ~p 시작~n", [DroneId]),
    loop(DroneId, #{alt => 50.0, bat => 100.0, lat => 37.5, lon => 127.0}).

loop(DroneId, State) ->
    receive
        {get_state, From} ->
            From ! {state, DroneId, State},
            loop(DroneId, State);
        {update, NewState} ->
            loop(DroneId, maps:merge(State, NewState));
        stop ->
            io:format("  드론 워커 ~p 중지~n", [DroneId])
    after 30000 ->
        loop(DroneId, State)
    end.
