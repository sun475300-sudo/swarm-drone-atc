%% Phase 575: Fault Supervisor — Erlang OTP
%% SDACS fault-tolerant drone supervision tree

-module(fault_supervisor).
-behaviour(supervisor).

-export([start_link/0, start_link/1, init/1]).
-export([add_drone/2, remove_drone/1, restart_drone/1, drone_status/1]).
-export([get_all_drones/0, supervisor_stats/0]).

%% Supervisor public API

start_link() ->
    start_link([]).

start_link(Args) ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, Args).

%% Supervisor callback

init(_Args) ->
    SupFlags = #{
        strategy  => one_for_one,
        intensity => 5,
        period    => 10
    },
    DroneSpecs = default_drone_specs(),
    {ok, {SupFlags, DroneSpecs}}.

%% Dynamic drone management

add_drone(DroneId, DroneConfig) ->
    ChildSpec = drone_child_spec(DroneId, DroneConfig),
    supervisor:start_child(?MODULE, ChildSpec).

remove_drone(DroneId) ->
    supervisor:terminate_child(?MODULE, DroneId),
    supervisor:delete_child(?MODULE, DroneId).

restart_drone(DroneId) ->
    supervisor:restart_child(?MODULE, DroneId).

drone_status(DroneId) ->
    Children = supervisor:which_children(?MODULE),
    case lists:keyfind(DroneId, 1, Children) of
        {DroneId, Pid, worker, _} when is_pid(Pid) ->
            {ok, running, Pid};
        {DroneId, undefined, worker, _} ->
            {ok, stopped};
        {DroneId, restarting, worker, _} ->
            {ok, restarting};
        false ->
            {error, not_found}
    end.

get_all_drones() ->
    Children = supervisor:which_children(?MODULE),
    [{Id, Status} || {Id, Status, worker, _} <- Children].

supervisor_stats() ->
    Children = supervisor:which_children(?MODULE),
    Running = length([P || {_, P, _, _} <- Children, is_pid(P)]),
    Stopped = length([P || {_, P, _, _} <- Children, P =:= undefined]),
    #{
        total    => length(Children),
        running  => Running,
        stopped  => Stopped,
        module   => ?MODULE
    }.

%% Internal helpers

drone_child_spec(DroneId, Config) ->
    #{
        id       => DroneId,
        start    => {drone_worker, start_link, [DroneId, Config]},
        restart  => transient,
        shutdown => 5000,
        type     => worker,
        modules  => [drone_worker]
    }.

default_drone_specs() ->
    %% Default drone workers started at supervisor init
    [].
