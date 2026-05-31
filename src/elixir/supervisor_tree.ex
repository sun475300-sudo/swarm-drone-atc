defmodule SDACS.SupervisorTree do
  @moduledoc """
  Phase 556 — Elixir OTP Supervisor tree for drone agents.

  Manages a multi-level Supervisor hierarchy:
    SDACS.SupervisorTree              (top-level, :one_for_one)
      ├── SDACS.FleetSupervisor       (manages N drone workers, :one_for_one)
      ├── SDACS.TelemetrySupervisor   (manages telemetry aggregators, :one_for_all)
      └── SDACS.ControlSupervisor     (manages ATC control processes, :rest_for_one)

  All restart strategies and child restart options follow OTP conventions.
  Phase 556 stub — child specs wired but worker logic is minimal.
  """

  use Supervisor

  # ── Public API ────────────────────────────────────────────────────────────────

  @spec start_link(keyword()) :: Supervisor.on_start()
  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl Supervisor
  def init(opts) do
    n_drones = Keyword.get(opts, :n_drones, 10)

    children = [
      {SDACS.FleetSupervisor,     [n_drones: n_drones]},
      {SDACS.TelemetrySupervisor, []},
      {SDACS.ControlSupervisor,   []}
    ]

    # Top-level uses :one_for_one — a crashed subsupervisor doesn't
    # affect siblings.  Max 3 restarts in 30 s before propagating.
    Supervisor.init(children, strategy: :one_for_one, max_restarts: 3, max_seconds: 30)
  end

  @doc "Return a summary of all running children."
  @spec tree_status() :: map()
  def tree_status do
    %{
      fleet:     child_count(SDACS.FleetSupervisor),
      telemetry: child_count(SDACS.TelemetrySupervisor),
      control:   child_count(SDACS.ControlSupervisor),
    }
  end

  defp child_count(sup) do
    case Process.whereis(sup) do
      nil -> 0
      _   -> sup |> Supervisor.which_children() |> length()
    end
  end
end

# ── Fleet Supervisor ──────────────────────────────────────────────────────────

defmodule SDACS.FleetSupervisor do
  @moduledoc """
  Supervises individual DroneWorker processes.
  Strategy: :one_for_one — a crashed drone worker is restarted independently.
  restart option: :permanent — workers always restart on termination.
  """

  use Supervisor

  @spec start_link(keyword()) :: Supervisor.on_start()
  def start_link(opts) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl Supervisor
  def init(opts) do
    n_drones = Keyword.get(opts, :n_drones, 10)

    children =
      for i <- 1..n_drones do
        drone_id = "D-#{String.pad_leading(Integer.to_string(i), 3, "0")}"
        # Each child spec uses restart: :permanent so workers always restart
        Supervisor.child_spec(
          {SDACS.DroneWorker, [drone_id: drone_id]},
          id:      String.to_atom("drone_worker_#{i}"),
          restart: :permanent
        )
      end

    Supervisor.init(children, strategy: :one_for_one, max_restarts: 10, max_seconds: 60)
  end
end

# ── Telemetry Supervisor ──────────────────────────────────────────────────────

defmodule SDACS.TelemetrySupervisor do
  @moduledoc """
  Supervises telemetry aggregation workers.
  Strategy: :one_for_all — if the aggregator crashes, the store restarts too.
  restart option: :permanent for aggregator, :transient for the store.
  """

  use Supervisor

  @spec start_link(keyword()) :: Supervisor.on_start()
  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl Supervisor
  def init(_opts) do
    children = [
      # Aggregator: always restart
      Supervisor.child_spec({SDACS.TelemetryAggregator, []},
                            id: :aggregator, restart: :permanent),
      # Store: restart only on abnormal exit
      Supervisor.child_spec({SDACS.TelemetryStore, []},
                            id: :store,      restart: :transient),
    ]

    Supervisor.init(children, strategy: :one_for_all, max_restarts: 5, max_seconds: 30)
  end
end

# ── Control Supervisor ────────────────────────────────────────────────────────

defmodule SDACS.ControlSupervisor do
  @moduledoc """
  Supervises ATC control processes.
  Strategy: :rest_for_one — if the conflict detector crashes, the resolver
  (which depends on it) also restarts.
  """

  use Supervisor

  @spec start_link(keyword()) :: Supervisor.on_start()
  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl Supervisor
  def init(_opts) do
    children = [
      {SDACS.ConflictDetector, []},
      {SDACS.ConflictResolver, []}
    ]

    Supervisor.init(children, strategy: :rest_for_one, max_restarts: 5, max_seconds: 30)
  end
end

# ── Worker Stubs ──────────────────────────────────────────────────────────────

defmodule SDACS.DroneWorker do
  @moduledoc "Minimal drone worker GenServer stub for Phase 556."
  use GenServer

  def start_link(opts) do
    drone_id = Keyword.fetch!(opts, :drone_id)
    GenServer.start_link(__MODULE__, drone_id, name: via(drone_id))
  end

  defp via(id), do: {:via, Registry, {SDACS.DroneRegistry, id}}

  @impl GenServer
  def init(drone_id) do
    {:ok, %{id: drone_id, pos: {0.0, 0.0, 50.0}, battery: 100.0, mode: :idle}}
  end

  @impl GenServer
  def handle_call(:state, _from, state), do: {:reply, state, state}
end

defmodule SDACS.TelemetryAggregator do
  use GenServer
  def start_link(opts \\ []), do: GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  @impl GenServer
  def init(_), do: {:ok, %{count: 0}}
  @impl GenServer
  def handle_cast({:ingest, _data}, %{count: c}), do: {:noreply, %{count: c + 1}}
end

defmodule SDACS.TelemetryStore do
  use GenServer
  def start_link(opts \\ []), do: GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  @impl GenServer
  def init(_), do: {:ok, %{}}
  @impl GenServer
  def handle_call({:get, id}, _from, state), do: {:reply, Map.get(state, id), state}
  @impl GenServer
  def handle_cast({:put, id, data}, state), do: {:noreply, Map.put(state, id, data)}
end

defmodule SDACS.ConflictDetector do
  use GenServer
  def start_link(opts \\ []), do: GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  @impl GenServer
  def init(_), do: {:ok, %{conflicts: []}}
end

defmodule SDACS.ConflictResolver do
  use GenServer
  def start_link(opts \\ []), do: GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  @impl GenServer
  def init(_), do: {:ok, %{resolved: 0}}
end
