%% Phase 575: Fault Supervisor Tree — Erlang
%% 드론 군집 장애 감독 트리: OTP supervisor 패턴,
%% 프로세스 모니터링, 자동 재시작, 장애 격리.

-module(fault_supervisor).
-behaviour(supervisor).

%% API
-export([start_link/0, start_drone/1, stop_drone/1,
         get_status/0, get_drone_count/0]).

%% Supervisor 콜백
-export([init/1]).

%% 드론 프로세스 모듈
-export([drone_init/1, drone_loop/1]).

%% ─── 레코드 정의 ───
-record(drone_state, {
    id        :: integer(),
    position  :: {float(), float(), float()},
    battery   :: float(),
    status    :: atom(),
    restarts  :: integer()
}).

%% ─── Supervisor API ───
start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    SupFlags = #{
        strategy  => one_for_one,
        intensity => 10,
        period    => 60
    },
    %% 초기 자식 프로세스 없음 (동적 추가)
    {ok, {SupFlags, []}}.

%% ─── 드론 프로세스 관리 ───
start_drone(DroneId) ->
    ChildSpec = #{
        id       => {drone, DroneId},
        start    => {?MODULE, drone_init, [DroneId]},
        restart  => permanent,
        shutdown => 5000,
        type     => worker,
        modules  => [?MODULE]
    },
    supervisor:start_child(?MODULE, ChildSpec).

stop_drone(DroneId) ->
    supervisor:terminate_child(?MODULE, {drone, DroneId}),
    supervisor:delete_child(?MODULE, {drone, DroneId}).

get_status() ->
    Children = supervisor:which_children(?MODULE),
    lists:map(fun({Id, Pid, _Type, _Modules}) ->
        {Id, Pid, is_process_alive(Pid)}
    end, Children).

get_drone_count() ->
    length(supervisor:which_children(?MODULE)).

%% ─── 드론 프로세스 ───
drone_init(DroneId) ->
    State = #drone_state{
        id       = DroneId,
        position = {0.0, 0.0, 0.0},
        battery  = 100.0,
        status   = idle,
        restarts = 0
    },
    Pid = spawn_link(fun() -> drone_loop(State) end),
    {ok, Pid}.

drone_loop(State) ->
    receive
        {get_state, From} ->
            From ! {drone_state, State},
            drone_loop(State);

        {update_position, {X, Y, Z}} ->
            NewState = State#drone_state{
                position = {X, Y, Z},
                status   = flying
            },
            drone_loop(NewState);

        {update_battery, Level} ->
            NewState = State#drone_state{battery = Level},
            case Level < 10.0 of
                true  ->
                    io:format("Drone ~p: LOW BATTERY (~.1f%)~n",
                              [State#drone_state.id, Level]),
                    drone_loop(NewState#drone_state{status = returning});
                false ->
                    drone_loop(NewState)
            end;

        {mission, MissionType} ->
            io:format("Drone ~p: Mission ~p started~n",
                      [State#drone_state.id, MissionType]),
            drone_loop(State#drone_state{status = MissionType});

        {inject_fault, FaultType} ->
            io:format("Drone ~p: FAULT ~p — crashing process~n",
                      [State#drone_state.id, FaultType]),
            exit({fault, FaultType});

        stop ->
            io:format("Drone ~p: Shutting down~n", [State#drone_state.id]),
            ok

    after 10000 ->
        %% 주기적 상태 보고
        NewBattery = State#drone_state.battery - 0.1,
        drone_loop(State#drone_state{battery = NewBattery})
    end.

%% ─── 유틸리티 ───
is_process_alive(Pid) when is_pid(Pid) ->
    erlang:is_process_alive(Pid);
is_process_alive(_) ->
    false.

%% ─── 테스트 실행 ───
%% erl -s fault_supervisor start_link
%% fault_supervisor:start_drone(1).
%% fault_supervisor:start_drone(2).
%% fault_supervisor:get_status().
%% fault_supervisor:get_drone_count().
