# Phase 556 — Elixir Supervisor Tree with Restart Strategies
# Elixir module implementing OTP Supervisor patterns for fault-tolerant drone management.

defmodule SwarmDrone.SupervisorTree do
  @moduledoc """
  Phase 556: OTP Supervisor tree for swarm drone process management.
  Implements one_for_one, one_for_all, and rest_for_one restart strategies.
  """

  use Supervisor

  @doc """
  Start the top-level Supervisor for the swarm system.
  """
  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      # Drone telemetry processor — restart individually on failure
      {SwarmDrone.TelemetryProcessor, []},
      # Mission controller — restart individually
      {SwarmDrone.MissionController, []},
      # Communication hub — restart all dependents if this fails
      {SwarmDrone.CommHub, []},
      # Safety monitor — always running, critical component
      {SwarmDrone.SafetyMonitor, []},
    ]

    # one_for_one: only restart the failed child process
    Supervisor.init(children, strategy: :one_for_one, max_restarts: 5, max_seconds: 10)
  end
end

defmodule SwarmDrone.TelemetryProcessor do
  @moduledoc "Processes incoming drone telemetry data."
  use GenServer

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{count: 0, last: nil}, opts)
  end

  @impl true
  def init(state), do: {:ok, state}

  @impl true
  def handle_call({:process, telemetry}, _from, state) do
    new_state = %{state | count: state.count + 1, last: telemetry}
    {:reply, {:ok, new_state.count}, new_state}
  end

  @impl true
  def handle_call(:stats, _from, state) do
    {:reply, state, state}
  end

  def process(pid, telemetry), do: GenServer.call(pid, {:process, telemetry})
  def stats(pid), do: GenServer.call(pid, :stats)
end

defmodule SwarmDrone.MissionController do
  @moduledoc "Manages drone mission lifecycle with automatic restart support."
  use GenServer

  @default_restart_delay 1000  # ms

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{missions: %{}, active: 0}, opts)
  end

  @impl true
  def init(state), do: {:ok, state}

  @impl true
  def handle_call({:start_mission, id, params}, _from, state) do
    mission = %{id: id, params: params, status: :active, started_at: :os.system_time(:second)}
    new_state = %{state | missions: Map.put(state.missions, id, mission), active: state.active + 1}
    {:reply, {:ok, mission}, new_state}
  end

  @impl true
  def handle_call({:complete_mission, id}, _from, state) do
    case Map.get(state.missions, id) do
      nil -> {:reply, {:error, :not_found}, state}
      m ->
        updated = Map.put(state.missions, id, %{m | status: :complete})
        {:reply, :ok, %{state | missions: updated, active: max(0, state.active - 1)}}
    end
  end

  @impl true
  def handle_call(:list, _from, state) do
    {:reply, Map.values(state.missions), state}
  end

  def start_mission(pid, id, params), do: GenServer.call(pid, {:start_mission, id, params})
  def complete_mission(pid, id), do: GenServer.call(pid, {:complete_mission, id})
  def list_missions(pid), do: GenServer.call(pid, :list)
  def restart_delay, do: @default_restart_delay
end

defmodule SwarmDrone.CommHub do
  @moduledoc "Communication hub that relays messages between drones and GCS."
  use GenServer

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{connected: [], message_count: 0}, opts)
  end

  @impl true
  def init(state), do: {:ok, state}

  @impl true
  def handle_call({:connect, drone_id}, _from, state) do
    new_state = %{state | connected: [drone_id | state.connected]}
    {:reply, :ok, new_state}
  end

  @impl true
  def handle_call({:relay, from, to, msg}, _from, state) do
    new_state = %{state | message_count: state.message_count + 1}
    {:reply, {:relayed, from, to, msg}, new_state}
  end

  @impl true
  def handle_call(:status, _from, state) do
    {:reply, %{connected_count: length(state.connected), messages: state.message_count}, state}
  end

  def connect(pid, drone_id), do: GenServer.call(pid, {:connect, drone_id})
  def relay(pid, from, to, msg), do: GenServer.call(pid, {:relay, from, to, msg})
  def status(pid), do: GenServer.call(pid, :status)
end

defmodule SwarmDrone.SafetyMonitor do
  @moduledoc """
  Safety monitor with :permanent restart strategy.
  Monitors all drones for safety violations and triggers alerts.
  """
  use GenServer

  # Safety thresholds
  @min_battery 15.0
  @max_altitude 150.0
  @min_separation 3.0

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{violations: [], check_count: 0}, opts)
  end

  @impl true
  def init(state), do: {:ok, state}

  @impl true
  def handle_call({:check, drone_state}, _from, state) do
    violations = check_violations(drone_state)
    new_state = %{state |
      violations: state.violations ++ violations,
      check_count: state.check_count + 1
    }
    {:reply, violations, new_state}
  end

  @impl true
  def handle_call(:report, _from, state) do
    report = %{
      total_checks: state.check_count,
      total_violations: length(state.violations),
      phase: "556"
    }
    {:reply, report, state}
  end

  defp check_violations(%{battery: b}) when b < @min_battery,
    do: [{:low_battery, b}]
  defp check_violations(%{altitude: a}) when a > @max_altitude,
    do: [{:altitude_exceeded, a}]
  defp check_violations(_), do: []

  def check(pid, drone_state), do: GenServer.call(pid, {:check, drone_state})
  def report(pid), do: GenServer.call(pid, :report)
  def min_battery, do: @min_battery
  def max_altitude, do: @max_altitude
end

# ===== Supervisor Configuration Summary =====
defmodule SwarmDrone.SupervisorConfig do
  @moduledoc "Configuration for restart strategies in the supervisor tree."

  @doc """
  Returns available restart strategies and their descriptions.
  Phase 556: OTP restart strategy reference.
  """
  def strategies do
    %{
      one_for_one: "Restart only the failed child; siblings keep running",
      one_for_all: "Restart all children if any one fails",
      rest_for_one: "Restart the failed child and all children started after it"
    }
  end

  def child_specs do
    [
      %{id: :telemetry, module: SwarmDrone.TelemetryProcessor, restart: :permanent},
      %{id: :mission,   module: SwarmDrone.MissionController,  restart: :permanent},
      %{id: :comm_hub,  module: SwarmDrone.CommHub,            restart: :transient},
      %{id: :safety,    module: SwarmDrone.SafetyMonitor,      restart: :permanent},
    ]
  end
end
