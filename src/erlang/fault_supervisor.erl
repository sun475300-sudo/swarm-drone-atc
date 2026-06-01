%% Fault Supervisor — Erlang OTP supervisor for SDACS drone fleet
%% Phase 575

-module(fault_supervisor).
-behaviour(supervisor).

-export([start_link/0, start_link/1]).
-export([init/1]).
-export([add_drone/1, remove_drone/1, list_drones/0, restart_drone/1]).

%% ─── API ────────────────────────────────────────────────────────

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

start_link(Args) ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, Args).

add_drone(DroneId) ->
    ChildSpec = drone_child_spec(DroneId),
    supervisor:start_child(?MODULE, ChildSpec).

remove_drone(DroneId) ->
    supervisor:terminate_child(?MODULE, DroneId),
    supervisor:delete_child(?MODULE, DroneId).

list_drones() ->
    Children = supervisor:which_children(?MODULE),
    [Id || {Id, _, _, _} <- Children].

restart_drone(DroneId) ->
    supervisor:restart_child(?MODULE, DroneId).

%% ─── Supervisor Callbacks ───────────────────────────────────────

init([]) ->
    SupFlags = #{
        strategy  => one_for_one,
        intensity => 5,
        period    => 10
    },
    ChildSpecs = [
        drone_child_spec(drone_001),
        drone_child_spec(drone_002),
        drone_child_spec(drone_003)
    ],
    {ok, {SupFlags, ChildSpecs}};

init(DroneIds) when is_list(DroneIds) ->
    SupFlags = #{
        strategy  => one_for_one,
        intensity => 5,
        period    => 10
    },
    ChildSpecs = [drone_child_spec(Id) || Id <- DroneIds],
    {ok, {SupFlags, ChildSpecs}}.

%% ─── Internal ───────────────────────────────────────────────────

drone_child_spec(DroneId) ->
    #{
        id       => DroneId,
        start    => {drone_worker, start_link, [DroneId]},
        restart  => permanent,
        shutdown => 5000,
        type     => worker,
        modules  => [drone_worker]
    }.

%% ─── Health Check ───────────────────────────────────────────────

health_check() ->
    Drones = list_drones(),
    Alive = length(Drones),
    io:format("Fault supervisor: ~p drone(s) alive~n", [Alive]),
    {ok, Alive}.
