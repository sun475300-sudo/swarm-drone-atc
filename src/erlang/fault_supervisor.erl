%% Phase 575 — Erlang fault supervisor module
%% SDACS drone fleet fault tolerance via OTP supervisor behaviour.
%% Supervises drone worker processes with a one-for-one restart strategy.

-module(fault_supervisor).
-behaviour(supervisor).

%% Public API
-export([start_link/0, add_drone/2, remove_drone/1]).

%% Supervisor callbacks
-export([init/1]).

%% Child spec record fields
-define(DEFAULT_MAX_RESTARTS, 5).
-define(DEFAULT_WINDOW_SEC,  30).
-define(CHILD_SHUTDOWN_MS,  5000).

%% ---------------------------------------------------------------
%% Public API
%% ---------------------------------------------------------------

%% Start the supervisor and register it under its module name.
start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

%% Dynamically add a drone worker child.
-spec add_drone(DroneId :: atom(), Args :: list()) -> supervisor:startchild_ret().
add_drone(DroneId, Args) ->
    ChildSpec = drone_child_spec(DroneId, Args),
    supervisor:start_child(?MODULE, ChildSpec).

%% Dynamically remove and terminate a drone worker child.
-spec remove_drone(DroneId :: atom()) -> ok | {error, term()}.
remove_drone(DroneId) ->
    case supervisor:terminate_child(?MODULE, DroneId) of
        ok ->
            supervisor:delete_child(?MODULE, DroneId);
        Error ->
            Error
    end.

%% ---------------------------------------------------------------
%% Supervisor callbacks
%% ---------------------------------------------------------------

init([]) ->
    SupFlags = #{
        strategy  => one_for_one,
        intensity => ?DEFAULT_MAX_RESTARTS,
        period    => ?DEFAULT_WINDOW_SEC
    },
    %% Static children: a fleet monitor and an event logger
    Children = [
        fleet_monitor_spec(),
        event_logger_spec()
    ],
    {ok, {SupFlags, Children}}.

%% ---------------------------------------------------------------
%% Internal helpers — child spec builders
%% ---------------------------------------------------------------

drone_child_spec(DroneId, Args) ->
    #{
        id       => DroneId,
        start    => {drone_worker, start_link, [DroneId | Args]},
        restart  => transient,
        shutdown => ?CHILD_SHUTDOWN_MS,
        type     => worker,
        modules  => [drone_worker]
    }.

fleet_monitor_spec() ->
    #{
        id       => fleet_monitor,
        start    => {fleet_monitor, start_link, []},
        restart  => permanent,
        shutdown => ?CHILD_SHUTDOWN_MS,
        type     => worker,
        modules  => [fleet_monitor]
    }.

event_logger_spec() ->
    #{
        id       => event_logger,
        start    => {event_logger, start_link, []},
        restart  => permanent,
        shutdown => 2000,
        type     => worker,
        modules  => [event_logger]
    }.

%% ---------------------------------------------------------------
%% Utility: list all running children with their PIDs
%% ---------------------------------------------------------------
-spec list_drones() -> [{atom(), pid() | undefined, worker | supervisor, list()}].
list_drones() ->
    supervisor:which_children(?MODULE).
