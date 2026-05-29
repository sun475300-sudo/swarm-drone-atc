# Phase 633: Fault Supervisor — Elixir OTP GenServer
# OTP GenServer 장애 감시 트리

defmodule SDACS.DroneWorker do
  use GenServer

  defstruct [:drone_id, :status, :battery, :position, :restart_count]

  def start_link(drone_id) do
    GenServer.start_link(__MODULE__, drone_id, name: via(drone_id))
  end

  def init(drone_id) do
    state = %__MODULE__{
      drone_id: drone_id,
      status: :idle,
      battery: 1.0,
      position: {0.0, 0.0, 0.0},
      restart_count: 0
    }
    {:ok, state}
  end

  def handle_call(:get_status, _from, state) do
    {:reply, state, state}
  end

  def handle_call({:update_position, pos}, _from, state) do
    {:reply, :ok, %{state | position: pos}}
  end

  def handle_call({:update_battery, level}, _from, state) do
    if level < 0.05 do
      {:stop, :battery_critical, :shutting_down, state}
    else
      {:reply, :ok, %{state | battery: level}}
    end
  end

  def handle_cast(:launch, state) do
    {:noreply, %{state | status: :flying}}
  end

  def handle_cast(:land, state) do
    {:noreply, %{state | status: :landed}}
  end

  def handle_info(:heartbeat, state) do
    Process.send_after(self(), :heartbeat, 1000)
    {:noreply, state}
  end

  defp via(drone_id), do: {:via, Registry, {SDACS.DroneRegistry, drone_id}}
end

defmodule SDACS.FaultSupervisor do
  use Supervisor

  def start_link(drone_ids) do
    Supervisor.start_link(__MODULE__, drone_ids, name: __MODULE__)
  end

  def init(drone_ids) do
    children = Enum.map(drone_ids, fn id ->
      %{
        id: id,
        start: {SDACS.DroneWorker, :start_link, [id]},
        restart: :permanent,
        shutdown: 5000,
        type: :worker
      }
    end)

    Supervisor.init(children, strategy: :one_for_one, max_restarts: 10, max_seconds: 60)
  end

  def get_fleet_status do
    Supervisor.which_children(__MODULE__)
    |> Enum.map(fn {id, pid, _type, _modules} ->
      if is_pid(pid) and Process.alive?(pid) do
        {id, GenServer.call(pid, :get_status)}
      else
        {id, :down}
      end
    end)
  end

  def count_active do
    Supervisor.count_children(__MODULE__)
  end
end
