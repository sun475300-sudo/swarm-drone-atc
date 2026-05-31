%% P575: FaultSupervisor - Erlang OTP fault supervision
%% Phase 575: Fault-tolerant drone supervision with automatic restart

-module(fault_supervisor).
-behaviour(supervisor).
-export([start_link/0, start_link/1, init/1,
         add_drone/2, remove_drone/1, list_drones/0]).

-define(MAX_RESTARTS, 5).
-define(MAX_PERIOD,   60).

%% Public API

start_link() ->
    start_link([]).

start_link(Opts) ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, Opts).

add_drone(DroneId, Args) ->
    ChildSpec = #{
        id       => DroneId,
        start    => {drone_worker, start_link, [DroneId, Args]},
        restart  => permanent,
        shutdown => 5000,
        type     => worker
    },
    supervisor:start_child(?MODULE, ChildSpec).

remove_drone(DroneId) ->
    supervisor:terminate_child(?MODULE, DroneId),
    supervisor:delete_child(?MODULE, DroneId).

list_drones() ->
    supervisor:which_children(?MODULE).

%% Supervisor callbacks

init(_Opts) ->
    SupFlags = #{
        strategy  => one_for_one,
        intensity => ?MAX_RESTARTS,
        period    => ?MAX_PERIOD
    },
    %% Initial child: fleet coordinator
    Children = [
        #{
            id       => fleet_coordinator,
            start    => {fleet_coordinator, start_link, []},
            restart  => permanent,
            shutdown => 10000,
            type     => worker
        }
    ],
    {ok, {SupFlags, Children}}.

%% ── drone_worker stub ──────────────────────────────────────────────────────
-module(drone_worker).
-behaviour(gen_server).
-export([start_link/2, stop/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-record(drone_state, {
    drone_id  :: binary(),
    status    :: idle | flying | charging | error,
    battery   :: float(),
    position  :: {float(), float(), float()},
    restarts  :: non_neg_integer()
}).

start_link(DroneId, _Args) ->
    gen_server:start_link(?MODULE, [DroneId], []).

stop(Pid) ->
    gen_server:stop(Pid).

init([DroneId]) ->
    State = #drone_state{
        drone_id = DroneId,
        status   = idle,
        battery  = 100.0,
        position = {0.0, 0.0, 0.0},
        restarts = 0
    },
    {ok, State}.

handle_call(get_status, _From, State) ->
    {reply, {ok, State#drone_state.status, State#drone_state.battery}, State};
handle_call(_Req, _From, State) ->
    {reply, ok, State}.

handle_cast({update_position, Pos}, State) ->
    {noreply, State#drone_state{position = Pos}};
handle_cast({battery_update, Level}, State) ->
    {noreply, State#drone_state{battery = Level}};
handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) -> {noreply, State}.
terminate(_Reason, _State) -> ok.
