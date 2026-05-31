%% fault_supervisor.erl - OTP Supervisor for drone fault management
%% SDACS swarm drone fault tolerance system

-module(fault_supervisor).
-behaviour(supervisor).

-export([start_link/0, start_link/1, init/1]).
-export([add_drone/2, remove_drone/1, get_drone_status/1, list_drones/0]).
-export([restart_drone/1, stop_drone/1]).

-define(MAX_RESTART, 5).
-define(MAX_TIME, 60).

%% Supervisor API
start_link() ->
    start_link(#{}).

start_link(Options) ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, Options).

%% Supervisor callback
init(_Options) ->
    SupFlags = #{
        strategy  => one_for_one,
        intensity => ?MAX_RESTART,
        period    => ?MAX_TIME
    },
    DroneSpecs = initial_drone_specs(),
    {ok, {SupFlags, DroneSpecs}}.

%% Generate initial drone worker specs
initial_drone_specs() ->
    [drone_spec(DroneId) || DroneId <- initial_drone_ids()].

initial_drone_ids() ->
    ["drone-001", "drone-002", "drone-003"].

drone_spec(DroneId) ->
    #{
        id       => list_to_atom("drone_" ++ DroneId),
        start    => {drone_worker, start_link, [DroneId]},
        restart  => transient,
        shutdown => 5000,
        type     => worker,
        modules  => [drone_worker]
    }.

%% Add a new drone to supervision
add_drone(DroneId, Config) ->
    Spec = #{
        id       => list_to_atom("drone_" ++ DroneId),
        start    => {drone_worker, start_link, [DroneId, Config]},
        restart  => temporary,
        shutdown => 2000,
        type     => worker,
        modules  => [drone_worker]
    },
    supervisor:start_child(?MODULE, Spec).

%% Remove drone from supervision tree
remove_drone(DroneId) ->
    Id = list_to_atom("drone_" ++ DroneId),
    supervisor:terminate_child(?MODULE, Id),
    supervisor:delete_child(?MODULE, Id).

%% Get status of specific drone
get_drone_status(DroneId) ->
    Id = list_to_atom("drone_" ++ DroneId),
    Children = supervisor:which_children(?MODULE),
    case lists:keyfind(Id, 1, Children) of
        {Id, Pid, _, _} when is_pid(Pid) -> {ok, running, Pid};
        {Id, undefined, _, _}             -> {ok, stopped};
        false                             -> {error, not_found}
    end.

%% List all supervised drones
list_drones() ->
    Children = supervisor:which_children(?MODULE),
    [{Id, Status} || {Id, Status, _, _} <- Children].

%% Restart a specific drone
restart_drone(DroneId) ->
    Id = list_to_atom("drone_" ++ DroneId),
    supervisor:terminate_child(?MODULE, Id),
    supervisor:restart_child(?MODULE, Id).

%% Stop drone gracefully
stop_drone(DroneId) ->
    remove_drone(DroneId).
