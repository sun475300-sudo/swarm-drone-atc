# Phase 556: supervisor_tree — Elixir 기반 군집 드론 Supervisor 트리
# SDACS Fault-Tolerant Supervisor Architecture

defmodule SDACS.Supervisor do
  @moduledoc """
  SDACS 최상위 Supervisor 트리.
  군집 드론 시스템의 결함 허용 아키텍처를 구현한다.
  """
  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.SwarmSupervisor, []},
      {SDACS.TelemetrySupervisor, []},
      {SDACS.SafetySupervisor, []},
    ]
    Supervisor.init(children, strategy: :one_for_one)
  end
end

defmodule SDACS.SwarmSupervisor do
  @moduledoc "드론 에이전트 프로세스 Supervisor"
  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.DroneRegistry, []},
      {SDACS.SwarmCoordinator, drone_count: 10},
    ]
    Supervisor.init(children, strategy: :rest_for_one)
  end

  def add_drone(drone_id) do
    spec = {SDACS.DroneAgent, drone_id: drone_id}
    Supervisor.start_child(__MODULE__, spec)
  end
end

defmodule SDACS.TelemetrySupervisor do
  @moduledoc "텔레메트리 수집·처리 Supervisor"
  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.TelemetryCollector, []},
      {SDACS.TelemetryProcessor, []},
      {SDACS.WebSocketBroadcaster, port: 8765},
    ]
    Supervisor.init(children, strategy: :one_for_all)
  end
end

defmodule SDACS.SafetySupervisor do
  @moduledoc "안전 모니터링 Supervisor — restart 정책: :permanent"
  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      %{
        id: SDACS.ConflictDetector,
        start: {SDACS.ConflictDetector, :start_link, [[]]},
        restart: :permanent,
        shutdown: 5_000,
        type: :worker,
      },
      %{
        id: SDACS.GeofenceMonitor,
        start: {SDACS.GeofenceMonitor, :start_link, [[]]},
        restart: :permanent,
        shutdown: 5_000,
        type: :worker,
      },
      %{
        id: SDACS.FailsafeManager,
        start: {SDACS.FailsafeManager, :start_link, [[]]},
        restart: :permanent,
        shutdown: 10_000,
        type: :worker,
      },
    ]
    Supervisor.init(children, strategy: :one_for_one)
  end
end

defmodule SDACS.DroneAgent do
  @moduledoc "개별 드론 에이전트 GenServer"
  use GenServer

  defstruct [:drone_id, :position, :battery, :mode, :is_armed]

  def start_link(opts) do
    drone_id = Keyword.fetch!(opts, :drone_id)
    GenServer.start_link(__MODULE__, drone_id, name: via_tuple(drone_id))
  end

  defp via_tuple(drone_id), do: {:via, Registry, {SDACS.DroneRegistry, drone_id}}

  @impl true
  def init(drone_id) do
    state = %__MODULE__{
      drone_id: drone_id,
      position: {37.5, 127.0, 0.0},
      battery: 100.0,
      mode: "STABILIZE",
      is_armed: false,
    }
    {:ok, state}
  end

  @impl true
  def handle_call(:get_status, _from, state) do
    {:reply, state, state}
  end

  @impl true
  def handle_cast({:command, "TAKEOFF", %{alt: alt}}, state) do
    {lat, lon, _} = state.position
    new_state = %{state | position: {lat, lon, alt}, is_armed: true, mode: "GUIDED"}
    {:noreply, new_state}
  end

  @impl true
  def handle_cast({:command, "LAND", _}, state) do
    {lat, lon, _} = state.position
    new_state = %{state | position: {lat, lon, 0.0}, is_armed: false}
    {:noreply, new_state}
  end

  @impl true
  def handle_cast({:command, cmd, _params}, state) do
    IO.puts("[DroneAgent #{state.drone_id}] Unknown command: #{cmd}")
    {:noreply, state}
  end

  def get_status(drone_id), do: GenServer.call(via_tuple(drone_id), :get_status)
  def send_command(drone_id, cmd, params \\ %{}),
    do: GenServer.cast(via_tuple(drone_id), {:command, cmd, params})
end

# Phase 556 진입점
IO.puts("SDACS Supervisor Tree — Phase 556 (Elixir OTP)")
IO.puts("Supervisor strategies: one_for_one, rest_for_one, one_for_all")
IO.puts("All critical workers use restart: :permanent")
