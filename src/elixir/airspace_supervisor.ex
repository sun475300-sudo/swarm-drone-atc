defmodule SDACS.AirspaceSupervisor do
  @moduledoc """
  SDACS 공역 감독자 — Elixir/OTP
  ================================
  Supervisor + GenServer 기반 장애 허용 관제 시스템

  기능:
    - OTP Supervisor 트리 (자동 재시작)
    - GenServer 기반 드론 프로세스
    - ETS 기반 공유 상태 (드론 위치)
    - 분산 노드 지원
    - 장애 격리 + 자동 복구
  """

  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.DroneRegistry, []},
      {SDACS.ConflictDetector, []},
      {SDACS.AlertBroadcaster, []},
      {SDACS.MetricsCollector, []}
    ]

    Supervisor.init(children, strategy: :one_for_one, max_restarts: 10, max_seconds: 60)
  end
end

defmodule SDACS.DroneRegistry do
  @moduledoc "드론 등록/상태 관리 GenServer"
  use GenServer

  defstruct drones: %{}, total_registered: 0

  def start_link(_opts) do
    GenServer.start_link(__MODULE__, %__MODULE__{}, name: __MODULE__)
  end

  def register(drone_id, opts \\ []) do
    GenServer.call(__MODULE__, {:register, drone_id, opts})
  end

  def update_position(drone_id, {x, y, z}) do
    GenServer.cast(__MODULE__, {:update_pos, drone_id, {x, y, z}})
  end

  def get_drone(drone_id) do
    GenServer.call(__MODULE__, {:get, drone_id})
  end

  def all_drones do
    GenServer.call(__MODULE__, :all)
  end

  def drone_count do
    GenServer.call(__MODULE__, :count)
  end

  def summary do
    GenServer.call(__MODULE__, :summary)
  end

  # ── Callbacks ──────────────────────────────────────

  @impl true
  def init(state) do
    :ets.new(:drone_positions, [:named_table, :public, read_concurrency: true])
    {:ok, state}
  end

  @impl true
  def handle_call({:register, drone_id, opts}, _from, state) do
    drone = %{
      id: drone_id,
      position: {0.0, 0.0, 50.0},
      velocity: {0.0, 0.0, 0.0},
      battery: Keyword.get(opts, :battery, 100.0),
      status: :active,
      type: Keyword.get(opts, :type, :delivery),
      registered_at: DateTime.utc_now()
    }

    drones = Map.put(state.drones, drone_id, drone)
    :ets.insert(:drone_positions, {drone_id, drone.position})

    {:reply, :ok, %{state | drones: drones, total_registered: state.total_registered + 1}}
  end

  @impl true
  def handle_call({:get, drone_id}, _from, state) do
    {:reply, Map.get(state.drones, drone_id), state}
  end

  @impl true
  def handle_call(:all, _from, state) do
    {:reply, Map.values(state.drones), state}
  end

  @impl true
  def handle_call(:count, _from, state) do
    {:reply, map_size(state.drones), state}
  end

  @impl true
  def handle_call(:summary, _from, state) do
    active = state.drones |> Map.values() |> Enum.count(&(&1.status == :active))
    avg_battery = if map_size(state.drones) > 0 do
      state.drones |> Map.values() |> Enum.map(& &1.battery) |> Enum.sum() |> Kernel./(map_size(state.drones))
    else
      0.0
    end

    {:reply, %{
      total: map_size(state.drones),
      active: active,
      avg_battery: Float.round(avg_battery, 1),
      total_registered: state.total_registered
    }, state}
  end

  @impl true
  def handle_cast({:update_pos, drone_id, pos}, state) do
    case Map.get(state.drones, drone_id) do
      nil -> {:noreply, state}
      drone ->
        updated = %{drone | position: pos}
        :ets.insert(:drone_positions, {drone_id, pos})
        {:noreply, %{state | drones: Map.put(state.drones, drone_id, updated)}}
    end
  end
end

defmodule SDACS.ConflictDetector do
  @moduledoc "충돌 감지 GenServer — 1Hz 주기 스캔"
  use GenServer

  @scan_interval 1000  # 1초

  defstruct conflicts: [], total_scans: 0, min_sep: 50.0

  def start_link(_opts) do
    GenServer.start_link(__MODULE__, %__MODULE__{}, name: __MODULE__)
  end

  def recent_conflicts do
    GenServer.call(__MODULE__, :recent)
  end

  @impl true
  def init(state) do
    Process.send_after(self(), :scan, @scan_interval)
    {:ok, state}
  end

  @impl true
  def handle_info(:scan, state) do
    drones = SDACS.DroneRegistry.all_drones()
    new_conflicts = detect_conflicts(drones, state.min_sep)

    if length(new_conflicts) > 0 do
      SDACS.AlertBroadcaster.broadcast({:conflicts, new_conflicts})
    end

    Process.send_after(self(), :scan, @scan_interval)

    {:noreply, %{state |
      conflicts: Enum.take(new_conflicts ++ state.conflicts, 100),
      total_scans: state.total_scans + 1
    }}
  end

  @impl true
  def handle_call(:recent, _from, state) do
    {:reply, Enum.take(state.conflicts, 10), state}
  end

  defp detect_conflicts(drones, min_sep) do
    for d1 <- drones,
        d2 <- drones,
        d1.id < d2.id,
        dist = position_distance(d1.position, d2.position),
        dist < min_sep * 2 do
      %{
        drone_a: d1.id,
        drone_b: d2.id,
        distance: Float.round(dist, 1),
        severity: classify_severity(dist, min_sep),
        timestamp: DateTime.utc_now()
      }
    end
  end

  defp position_distance({x1, y1, z1}, {x2, y2, z2}) do
    :math.sqrt(:math.pow(x1 - x2, 2) + :math.pow(y1 - y2, 2) + :math.pow(z1 - z2, 2))
  end

  defp classify_severity(dist, min_sep) when dist < min_sep * 0.5, do: :critical
  defp classify_severity(dist, min_sep) when dist < min_sep, do: :high
  defp classify_severity(dist, min_sep) when dist < min_sep * 1.5, do: :medium
  defp classify_severity(_, _), do: :low
end

defmodule SDACS.AlertBroadcaster do
  @moduledoc "경보 브로드캐스트 GenServer"
  use GenServer

  def start_link(_opts), do: GenServer.start_link(__MODULE__, [], name: __MODULE__)
  def broadcast(alert), do: GenServer.cast(__MODULE__, {:broadcast, alert})
  def recent, do: GenServer.call(__MODULE__, :recent)

  @impl true
  def init(_), do: {:ok, []}

  @impl true
  def handle_cast({:broadcast, alert}, state) do
    {:noreply, Enum.take([alert | state], 100)}
  end

  @impl true
  def handle_call(:recent, _from, state), do: {:reply, Enum.take(state, 10), state}
end

defmodule SDACS.MetricsCollector do
  @moduledoc "메트릭 수집 GenServer"
  use GenServer

  def start_link(_opts), do: GenServer.start_link(__MODULE__, %{}, name: __MODULE__)
  def record(key, value), do: GenServer.cast(__MODULE__, {:record, key, value})
  def get(key), do: GenServer.call(__MODULE__, {:get, key})

  @impl true
  def init(_), do: {:ok, %{}}

  @impl true
  def handle_cast({:record, key, value}, state) do
    values = Map.get(state, key, [])
    {:noreply, Map.put(state, key, Enum.take([value | values], 500))}
  end

  @impl true
  def handle_call({:get, key}, _from, state) do
    {:reply, Map.get(state, key, []), state}
  end
end
