defmodule SDACS.SupervisorTree do
  @moduledoc """
  Phase 556: Fault-tolerant Supervisor tree for swarm drone system.
  OTP Supervisor with restart strategies for resilient operations.
  """

  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.DroneRegistry, []},
      {SDACS.TelemetryWorker, restart: :permanent},
      {SDACS.ConflictResolver, restart: :transient},
      {SDACS.APFController, restart: :permanent},
      {SDACS.HealthMonitor, restart: :temporary},
    ]

    # One-for-one restart: only restart the failed child
    Supervisor.init(children, strategy: :one_for_one, max_restarts: 5, max_seconds: 10)
  end

  def child_count do
    __MODULE__
    |> Supervisor.which_children()
    |> length()
  end
end

defmodule SDACS.DroneRegistry do
  @moduledoc "Registry for tracking active drone agents."
  use GenServer

  @restart :permanent

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{}, opts ++ [name: __MODULE__])
  end

  @impl true
  def init(state) do
    {:ok, state}
  end

  def register(drone_id, pid) do
    GenServer.cast(__MODULE__, {:register, drone_id, pid})
  end

  def lookup(drone_id) do
    GenServer.call(__MODULE__, {:lookup, drone_id})
  end

  @impl true
  def handle_cast({:register, drone_id, pid}, state) do
    {:noreply, Map.put(state, drone_id, pid)}
  end

  @impl true
  def handle_call({:lookup, drone_id}, _from, state) do
    {:reply, Map.get(state, drone_id), state}
  end
end

defmodule SDACS.TelemetryWorker do
  @moduledoc "Telemetry collection worker with permanent restart strategy."
  use GenServer

  @restart :permanent

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{count: 0, data: []}, opts ++ [name: __MODULE__])
  end

  @impl true
  def init(state) do
    schedule_collection()
    {:ok, state}
  end

  @impl true
  def handle_info(:collect, state) do
    new_state = %{state | count: state.count + 1}
    schedule_collection()
    {:noreply, new_state}
  end

  @impl true
  def handle_call(:get_count, _from, state) do
    {:reply, state.count, state}
  end

  defp schedule_collection do
    Process.send_after(self(), :collect, 1000)
  end

  def get_count do
    GenServer.call(__MODULE__, :get_count)
  end
end

defmodule SDACS.ConflictResolver do
  @moduledoc "Conflict resolution with transient restart (restarts on crash, not normal exit)."
  use GenServer

  @restart :transient

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, [], opts ++ [name: __MODULE__])
  end

  @impl true
  def init(conflicts) do
    {:ok, conflicts}
  end

  def report_conflict(conflict) do
    GenServer.cast(__MODULE__, {:conflict, conflict})
  end

  @impl true
  def handle_cast({:conflict, conflict}, conflicts) do
    {:noreply, [conflict | conflicts]}
  end

  @impl true
  def handle_call(:list_conflicts, _from, conflicts) do
    {:reply, conflicts, conflicts}
  end

  def list_conflicts do
    GenServer.call(__MODULE__, :list_conflicts)
  end
end

defmodule SDACS.APFController do
  @moduledoc "Artificial Potential Field controller with permanent restart."
  use GenServer

  @restart :permanent
  @apf_params %{repulsion: 5.0, attraction: 2.0, max_force: 10.0}

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, @apf_params, opts ++ [name: __MODULE__])
  end

  @impl true
  def init(params) do
    {:ok, params}
  end

  def compute_force(pos, goal, obstacles) do
    GenServer.call(__MODULE__, {:compute, pos, goal, obstacles})
  end

  @impl true
  def handle_call({:compute, pos, goal, _obstacles}, _from, params) do
    dx = elem(goal, 0) - elem(pos, 0)
    dy = elem(goal, 1) - elem(pos, 1)
    dist = :math.sqrt(dx * dx + dy * dy)
    force = if dist > 0 do
      scale = min(params.attraction, params.max_force) / max(dist, 0.1)
      {dx * scale, dy * scale}
    else
      {0.0, 0.0}
    end
    {:reply, force, params}
  end
end

defmodule SDACS.HealthMonitor do
  @moduledoc "Health monitoring with temporary restart (not restarted on exit)."
  use GenServer

  @restart :temporary

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{checks: 0, alerts: []}, opts ++ [name: __MODULE__])
  end

  @impl true
  def init(state) do
    {:ok, state}
  end

  def check_health do
    GenServer.call(__MODULE__, :health_check)
  end

  @impl true
  def handle_call(:health_check, _from, state) do
    new_state = %{state | checks: state.checks + 1}
    {:reply, :ok, new_state}
  end
end
