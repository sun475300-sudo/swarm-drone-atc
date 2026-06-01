%% Phase 575: Fault Supervisor — 드론 OTP 장애 수퍼바이저 (Erlang)
%% OTP supervisor for fault-tolerant drone fleet management.
-module(fault_supervisor).
-behaviour(supervisor).

-export([start_link/0, init/1]).
-export([start_drone/1, stop_drone/1, list_drones/0]).

%% ── Supervisor start ─────────────────────────────────────────────

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

%% ── Supervisor init ───────────────────────────────────────────────

init([]) ->
    SupFlags = #{
        strategy  => one_for_one,
        intensity => 5,
        period    => 10
    },
    DroneSpecs = [drone_spec(I) || I <- lists:seq(1, 4)],
    {ok, {SupFlags, DroneSpecs}}.

drone_spec(Id) ->
    #{
        id       => {drone_worker, Id},
        start    => {drone_worker, start_link, [Id]},
        restart  => permanent,
        shutdown => 5000,
        type     => worker,
        modules  => [drone_worker]
    }.

%% ── Dynamic drone management ──────────────────────────────────────

start_drone(Id) ->
    Spec = drone_spec(Id),
    supervisor:start_child(?MODULE, Spec).

stop_drone(Id) ->
    supervisor:terminate_child(?MODULE, {drone_worker, Id}),
    supervisor:delete_child(?MODULE, {drone_worker, Id}).

list_drones() ->
    supervisor:which_children(?MODULE).

%% ── Module drone_worker ───────────────────────────────────────────

-module(drone_worker).
-behaviour(gen_server).

-export([start_link/1, init/1, handle_call/3, handle_cast/2, handle_info/2]).
-export([get_state/1, send_command/2]).

-record(drone_state, {
    id       :: integer(),
    x = 0.0  :: float(),
    y = 0.0  :: float(),
    z = 50.0 :: float(),
    battery = 100.0 :: float(),
    status = active :: atom(),
    tick = 0 :: integer()
}).

start_link(Id) ->
    gen_server:start_link({local, drone_name(Id)}, ?MODULE, [Id], []).

init([Id]) ->
    self() ! tick,
    {ok, #drone_state{id = Id}}.

handle_call(get_state, _From, State) ->
    Info = #{id      => State#drone_state.id,
             x       => State#drone_state.x,
             y       => State#drone_state.y,
             z       => State#drone_state.z,
             battery => State#drone_state.battery,
             status  => State#drone_state.status},
    {reply, Info, State};
handle_call({command, Cmd}, _From, State) ->
    NewState = apply_command(Cmd, State),
    {reply, ok, NewState}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(tick, State) ->
    erlang:send_after(100, self(), tick),
    NewState = State#drone_state{
        battery = max(0.0, State#drone_state.battery - 0.01),
        tick    = State#drone_state.tick + 1
    },
    {noreply, NewState};
handle_info(_Info, State) ->
    {noreply, State}.

get_state(Id) ->
    gen_server:call(drone_name(Id), get_state).

send_command(Id, Cmd) ->
    gen_server:call(drone_name(Id), {command, Cmd}).

apply_command(hover,   State) -> State#drone_state{status = hovering};
apply_command(land,    State) -> State#drone_state{status = landing, z = 0.0};
apply_command(takeoff, State) -> State#drone_state{status = active, z = 50.0};
apply_command(_Other,  State) -> State.

drone_name(Id) ->
    list_to_atom("drone_" ++ integer_to_list(Id)).
