# P556: SupervisorTree - Elixir fault-tolerant supervisor tree
# Phase 556: OTP supervision tree for drone fleet management

defmodule SDACS.SupervisorTree do
  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.FleetCoordinator, []},
      {SDACS.TelemetryIngester, []},
      {SDACS.ConflictResolver, []},
      {SDACS.HealthMonitor, []},
    ]
    Supervisor.init(children, strategy: :one_for_one)
  end

  # Restart a specific child by name
  def restart_child(child_id) do
    Supervisor.terminate_child(__MODULE__, child_id)
    Supervisor.restart_child(__MODULE__, child_id)
  end

  def which_children do
    Supervisor.which_children(__MODULE__)
  end
end

defmodule SDACS.FleetCoordinator do
  use GenServer

  @moduledoc """
  Coordinates drone fleet assignments and mission planning.
  Restart strategy: permanent (always restart on failure).
  """

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{drones: %{}, missions: []}, name: __MODULE__)
  end

  @impl true
  def init(state), do: {:ok, state}

  def assign_mission(drone_id, mission) do
    GenServer.call(__MODULE__, {:assign, drone_id, mission})
  end

  def get_fleet_status do
    GenServer.call(__MODULE__, :status)
  end

  @impl true
  def handle_call({:assign, drone_id, mission}, _from, state) do
    new_drones = Map.put(state.drones, drone_id, %{mission: mission, status: :assigned})
    {:reply, :ok, %{state | drones: new_drones}}
  end

  @impl true
  def handle_call(:status, _from, state) do
    {:reply, state, state}
  end
end

defmodule SDACS.TelemetryIngester do
  use GenServer

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{frames: [], count: 0}, name: __MODULE__)
  end

  @impl true
  def init(state), do: {:ok, state}

  def ingest(frame) do
    GenServer.cast(__MODULE__, {:ingest, frame})
  end

  @impl true
  def handle_cast({:ingest, frame}, state) do
    {:noreply, %{state | frames: [frame | state.frames], count: state.count + 1}}
  end
end

defmodule SDACS.ConflictResolver do
  use GenServer

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{conflicts: []}, name: __MODULE__)
  end

  @impl true
  def init(state), do: {:ok, state}

  def resolve(conflict) do
    GenServer.call(__MODULE__, {:resolve, conflict})
  end

  @impl true
  def handle_call({:resolve, conflict}, _from, state) do
    resolution = %{conflict: conflict, action: :hold, timestamp: System.monotonic_time()}
    {:reply, resolution, %{state | conflicts: [resolution | state.conflicts]}}
  end
end

defmodule SDACS.HealthMonitor do
  use GenServer

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{alerts: []}, name: __MODULE__)
  end

  @impl true
  def init(state), do: {:ok, state}
end
