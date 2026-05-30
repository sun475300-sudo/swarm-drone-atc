defmodule SDACS.FaultSupervisor do
  @moduledoc """
  SDACS 드론 군집 결함 감지 및 복구 슈퍼바이저
  OTP Supervisor를 활용한 내결함성 아키텍처
  """

  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.DroneRegistry, name: SDACS.DroneRegistry},
      {SDACS.HealthMonitor, interval: 1000},
      {SDACS.AlertDispatcher, []},
    ]
    Supervisor.init(children, strategy: :one_for_one)
  end

  def child_count do
    Supervisor.count_children(__MODULE__)
  end
end

defmodule SDACS.DroneRegistry do
  @moduledoc "드론 상태 레지스트리"
  use GenServer

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{}, opts)
  end

  @impl true
  def init(state), do: {:ok, state}

  def register(pid, drone_id, status) do
    GenServer.call(pid, {:register, drone_id, status})
  end

  def get_status(pid, drone_id) do
    GenServer.call(pid, {:get, drone_id})
  end

  def list_drones(pid) do
    GenServer.call(pid, :list)
  end

  @impl true
  def handle_call({:register, id, status}, _from, state) do
    {:reply, :ok, Map.put(state, id, status)}
  end

  def handle_call({:get, id}, _from, state) do
    {:reply, Map.get(state, id, :not_found), state}
  end

  def handle_call(:list, _from, state) do
    {:reply, Map.keys(state), state}
  end
end

defmodule SDACS.HealthMonitor do
  @moduledoc "드론 헬스 모니터링 GenServer"
  use GenServer

  defstruct [:interval, :checks, :failures]

  def start_link(opts \\ []) do
    interval = Keyword.get(opts, :interval, 5000)
    GenServer.start_link(__MODULE__, %{interval: interval, checks: 0, failures: 0}, name: __MODULE__)
  end

  @impl true
  def init(state) do
    schedule_check(state.interval)
    {:ok, state}
  end

  @impl true
  def handle_info(:health_check, state) do
    new_state = %{state | checks: state.checks + 1}
    schedule_check(state.interval)
    {:noreply, new_state}
  end

  def handle_call(:status, _from, state) do
    {:reply, state, state}
  end

  defp schedule_check(interval) do
    Process.send_after(self(), :health_check, interval)
  end
end

defmodule SDACS.AlertDispatcher do
  @moduledoc "결함 알림 디스패처"
  use GenServer

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, [], opts)
  end

  @impl true
  def init(_), do: {:ok, []}

  def dispatch(pid, alert) do
    GenServer.cast(pid, {:dispatch, alert})
  end

  @impl true
  def handle_cast({:dispatch, alert}, alerts) do
    {:noreply, [alert | alerts]}
  end

  def handle_call(:list, _from, alerts) do
    {:reply, alerts, alerts}
  end
end
