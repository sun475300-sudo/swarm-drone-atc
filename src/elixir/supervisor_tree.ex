defmodule SDACS.SupervisorTree do
  @moduledoc """
  SDACS 드론 군집 슈퍼바이저 트리 (Phase 556)
  OTP Supervisor 계층 구조 + restart 정책
  """

  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.FleetController, []},
      {SDACS.TelemetryAggregator, interval: 100},
      {SDACS.ConflictDetector, threshold: 50.0},
      {SDACS.AlertDispatcherSvc, []},
    ]
    # one_for_one: 한 자식 crash 시 해당 자식만 restart
    Supervisor.init(children, strategy: :one_for_one, max_restarts: 5, max_seconds: 10)
  end

  def restart_child(module) do
    Supervisor.restart_child(__MODULE__, module)
  end

  def child_count do
    Supervisor.count_children(__MODULE__)
  end
end

defmodule SDACS.FleetController do
  @moduledoc "드론 군집 제어 GenServer"
  use GenServer

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{drones: %{}, tick: 0}, name: __MODULE__)
  end

  @impl true
  def init(state), do: {:ok, state}

  def register_drone(drone_id, status) do
    GenServer.call(__MODULE__, {:register, drone_id, status})
  end

  def get_fleet_status do
    GenServer.call(__MODULE__, :fleet_status)
  end

  @impl true
  def handle_call({:register, id, status}, _from, state) do
    {:reply, :ok, put_in(state, [:drones, id], status)}
  end

  def handle_call(:fleet_status, _from, state) do
    {:reply, state.drones, state}
  end

  def handle_info(:tick, state) do
    {:noreply, %{state | tick: state.tick + 1}}
  end
end

defmodule SDACS.TelemetryAggregator do
  @moduledoc "텔레메트리 집계 (restart 가능)"
  use GenServer

  def start_link(opts \\ []) do
    interval = Keyword.get(opts, :interval, 1000)
    GenServer.start_link(__MODULE__, %{frames: [], interval: interval}, name: __MODULE__)
  end

  @impl true
  def init(state) do
    schedule(state.interval)
    {:ok, state}
  end

  def ingest(frame) do
    GenServer.cast(__MODULE__, {:ingest, frame})
  end

  def get_frames do
    GenServer.call(__MODULE__, :get_frames)
  end

  @impl true
  def handle_cast({:ingest, frame}, state) do
    {:noreply, %{state | frames: [frame | Enum.take(state.frames, 999)]}}
  end

  def handle_call(:get_frames, _from, state) do
    {:reply, state.frames, state}
  end

  def handle_info(:aggregate, state) do
    schedule(state.interval)
    {:noreply, state}
  end

  defp schedule(ms), do: Process.send_after(self(), :aggregate, ms)
end

defmodule SDACS.ConflictDetector do
  @moduledoc "충돌 감지 서비스 (restart 정책: permanent)"
  use GenServer

  def start_link(opts \\ []) do
    threshold = Keyword.get(opts, :threshold, 50.0)
    GenServer.start_link(__MODULE__, %{threshold: threshold, alerts: []}, name: __MODULE__)
  end

  @impl true
  def init(state), do: {:ok, state}

  def check_pair(drone_a, drone_b, distance) do
    GenServer.call(__MODULE__, {:check, drone_a, drone_b, distance})
  end

  @impl true
  def handle_call({:check, a, b, dist}, _from, state) do
    if dist < state.threshold do
      alert = %{drones: {a, b}, distance: dist, ts: System.monotonic_time(:millisecond)}
      {:reply, {:conflict, alert}, %{state | alerts: [alert | state.alerts]}}
    else
      {:reply, :clear, state}
    end
  end

  def handle_call(:alerts, _from, state), do: {:reply, state.alerts, state}
end

defmodule SDACS.AlertDispatcherSvc do
  use GenServer

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, [], name: __MODULE__)
  end

  @impl true
  def init(_), do: {:ok, []}

  def dispatch(alert) do
    GenServer.cast(__MODULE__, {:dispatch, alert})
  end

  @impl true
  def handle_cast({:dispatch, alert}, alerts) do
    {:noreply, [alert | alerts]}
  end
end
