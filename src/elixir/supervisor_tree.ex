defmodule SDACS.SupervisorTree do
  @moduledoc """
  Phase 556: Supervisor Tree — Elixir OTP
  SDACS fault-tolerant drone fleet supervision using OTP supervision trees.

  Implements a hierarchical supervision tree:
  - FleetSupervisor (one_for_one)
    - DroneSupervisor per zone (rest_for_one)
      - DroneWorker per drone (transient)
      - TelemetryCollector per zone
  """

  use Supervisor

  # Phase 556 marker — Supervisor with restart strategies

  @type drone_id :: String.t()
  @type zone_id  :: String.t()

  # ============================================================
  # Fleet Supervisor (top-level)

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.FleetRegistry, []},
      {SDACS.ZoneSupervisor, zone_id: "zone_alpha"},
      {SDACS.ZoneSupervisor, zone_id: "zone_beta"},
      {SDACS.FleetMonitor, []},
    ]

    Supervisor.init(children, strategy: :one_for_one)
  end

  # ============================================================
  # Add/remove drones dynamically

  def add_drone(zone_id, drone_id, config) do
    SDACS.ZoneSupervisor.add_drone(zone_id, drone_id, config)
  end

  def remove_drone(zone_id, drone_id) do
    SDACS.ZoneSupervisor.remove_drone(zone_id, drone_id)
  end

  def restart_drone(zone_id, drone_id) do
    SDACS.ZoneSupervisor.restart_drone(zone_id, drone_id)
  end

  def fleet_status do
    SDACS.FleetMonitor.status()
  end
end

defmodule SDACS.ZoneSupervisor do
  @moduledoc """
  Manages all drones within a geographic zone.
  Uses rest_for_one so telemetry collector restarts with any worker failure.
  """
  use Supervisor

  def start_link(opts) do
    zone_id = Keyword.fetch!(opts, :zone_id)
    Supervisor.start_link(__MODULE__, opts, name: via(zone_id))
  end

  defp via(zone_id), do: {:via, Registry, {SDACS.FleetRegistry, zone_id}}

  @impl true
  def init(opts) do
    zone_id = Keyword.fetch!(opts, :zone_id)
    children = [
      {SDACS.TelemetryCollector, zone_id: zone_id},
    ]
    Supervisor.init(children, strategy: :rest_for_one)
  end

  def add_drone(zone_id, drone_id, config) do
    spec = drone_child_spec(drone_id, config)
    Supervisor.start_child(via(zone_id), spec)
  end

  def remove_drone(zone_id, drone_id) do
    sup = via(zone_id)
    :ok = Supervisor.terminate_child(sup, drone_id)
    :ok = Supervisor.delete_child(sup, drone_id)
  end

  def restart_drone(zone_id, drone_id) do
    Supervisor.restart_child(via(zone_id), drone_id)
  end

  defp drone_child_spec(drone_id, config) do
    %{
      id:       drone_id,
      start:    {SDACS.DroneWorker, :start_link, [[drone_id: drone_id, config: config]]},
      restart:  :transient,
      shutdown: 5_000,
      type:     :worker,
    }
  end
end

defmodule SDACS.DroneWorker do
  @moduledoc "GenServer managing a single drone's state and command queue."
  use GenServer

  @heartbeat_interval 1_000  # ms

  def start_link(opts) do
    drone_id = Keyword.fetch!(opts, :drone_id)
    GenServer.start_link(__MODULE__, opts, name: via(drone_id))
  end

  defp via(drone_id), do: {:via, Registry, {SDACS.FleetRegistry, {:drone, drone_id}}}

  @impl true
  def init(opts) do
    drone_id = Keyword.fetch!(opts, :drone_id)
    config   = Keyword.get(opts, :config, %{})
    schedule_heartbeat()
    {:ok, %{
      drone_id: drone_id,
      battery:  Map.get(config, :battery, 100.0),
      altitude: 0.0,
      mode:     :idle,
      position: {0.0, 0.0, 0.0},
      tick:     0,
    }}
  end

  @impl true
  def handle_call(:get_state, _from, state), do: {:reply, state, state}

  @impl true
  def handle_cast({:command, cmd}, state) do
    new_state = apply_command(cmd, state)
    {:noreply, new_state}
  end

  @impl true
  def handle_info(:heartbeat, state) do
    schedule_heartbeat()
    new_state = %{state |
      battery: max(0.0, state.battery - 0.01),
      tick: state.tick + 1,
    }
    {:noreply, new_state}
  end

  defp schedule_heartbeat, do: Process.send_after(self(), :heartbeat, @heartbeat_interval)

  defp apply_command(:takeoff, state), do: %{state | mode: :flying, altitude: 60.0}
  defp apply_command(:land, state),    do: %{state | mode: :landing, altitude: 0.0}
  defp apply_command(:rtl, state),     do: %{state | mode: :rtl, altitude: 0.0}
  defp apply_command(_, state),        do: state

  # Public API
  def get_state(drone_id),       do: GenServer.call(via(drone_id), :get_state)
  def command(drone_id, cmd),    do: GenServer.cast(via(drone_id), {:command, cmd})
end

defmodule SDACS.TelemetryCollector do
  @moduledoc "Collects and aggregates telemetry from drones in a zone."
  use GenServer

  def start_link(opts) do
    zone_id = Keyword.fetch!(opts, :zone_id)
    GenServer.start_link(__MODULE__, opts, name: via(zone_id))
  end

  defp via(zone_id), do: {:via, Registry, {SDACS.FleetRegistry, {:telemetry, zone_id}}}

  @impl true
  def init(opts) do
    {:ok, %{zone_id: Keyword.fetch!(opts, :zone_id), frames: [], count: 0}}
  end

  @impl true
  def handle_cast({:ingest, frame}, state) do
    {:noreply, %{state | frames: [frame | Enum.take(state.frames, 999)], count: state.count + 1}}
  end

  def ingest(zone_id, frame), do: GenServer.cast(via(zone_id), {:ingest, frame})
  def count(zone_id),         do: GenServer.call(via(zone_id), :count)
  def handle_call(:count, _from, state), do: {:reply, state.count, state}
end

defmodule SDACS.FleetRegistry do
  def start_link(_opts), do: Registry.start_link(keys: :unique, name: __MODULE__)
  def child_spec(opts), do: %{id: __MODULE__, start: {__MODULE__, :start_link, [opts]}}
end

defmodule SDACS.FleetMonitor do
  use GenServer
  def start_link(_opts), do: GenServer.start_link(__MODULE__, %{}, name: __MODULE__)
  def status, do: GenServer.call(__MODULE__, :status)
  @impl true
  def init(state), do: {:ok, Map.put(state, :started_at, DateTime.utc_now())}
  @impl true
  def handle_call(:status, _from, state), do: {:reply, state, state}
end
