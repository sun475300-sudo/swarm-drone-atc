%% SDACS Fault Supervisor — Erlang/OTP
%% Supervises drone agent processes and handles fault recovery.

-module(fault_supervisor).
-behaviour(supervisor).

-export([start_link/0, start_link/1, init/1]).
-export([add_drone/2, remove_drone/1, get_drone_pid/1, list_drones/0]).

%% Types
-type drone_id() :: binary() | atom().
-type drone_spec() :: #{id => drone_id(), module => atom(), args => list()}.

%% Supervisor startup
-spec start_link() -> {ok, pid()} | {error, term()}.
start_link() ->
    start_link([]).

-spec start_link(list()) -> {ok, pid()} | {error, term()}.
start_link(Args) ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, Args).

%% Supervisor init callback
-spec init(list()) -> {ok, {supervisor:sup_flags(), [supervisor:child_spec()]}}.
init(_Args) ->
    SupFlags = #{
        strategy  => one_for_one,
        intensity => 5,
        period    => 10
    },
    %% Initial drone child specs (empty — drones added dynamically)
    ChildSpecs = [],
    {ok, {SupFlags, ChildSpecs}}.

%% Dynamic drone management

-spec add_drone(drone_id(), drone_spec()) -> supervisor:startchild_ret().
add_drone(DroneId, #{module := Mod, args := Args}) ->
    ChildSpec = drone_child_spec(DroneId, Mod, Args),
    supervisor:start_child(?MODULE, ChildSpec).

-spec remove_drone(drone_id()) -> ok | {error, term()}.
remove_drone(DroneId) ->
    case supervisor:terminate_child(?MODULE, DroneId) of
        ok -> supervisor:delete_child(?MODULE, DroneId);
        Err -> Err
    end.

-spec get_drone_pid(drone_id()) -> pid() | undefined.
get_drone_pid(DroneId) ->
    Children = supervisor:which_children(?MODULE),
    case lists:keyfind(DroneId, 1, Children) of
        {DroneId, Pid, _, _} when is_pid(Pid) -> Pid;
        _ -> undefined
    end.

-spec list_drones() -> [drone_id()].
list_drones() ->
    [Id || {Id, Pid, _, _} <- supervisor:which_children(?MODULE), is_pid(Pid)].

%% Internal helpers

-spec drone_child_spec(drone_id(), atom(), list()) -> supervisor:child_spec().
drone_child_spec(DroneId, Module, Args) ->
    #{
        id       => DroneId,
        start    => {Module, start_link, [DroneId | Args]},
        restart  => transient,
        shutdown => 5000,
        type     => worker,
        modules  => [Module]
    }.
