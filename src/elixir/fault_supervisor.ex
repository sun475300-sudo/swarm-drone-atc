defmodule SDACS.FaultSupervisor do
  @moduledoc """
  Phase 633: Fault Supervisor — Elixir
  SDACS fault detection and recovery supervisor for drone fleet.
  """
  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.FaultDetector, []},
      {SDACS.RecoveryManager, []},
    ]
    Supervisor.init(children, strategy: :one_for_one)
  end

  def report_fault(drone_id, fault_type, details) do
    SDACS.FaultDetector.handle_fault(drone_id, fault_type, details)
  end
end

defmodule SDACS.FaultDetector do
  use GenServer

  def start_link(_opts), do: GenServer.start_link(__MODULE__, %{}, name: __MODULE__)
  def handle_fault(drone_id, type, details),
    do: GenServer.cast(__MODULE__, {:fault, drone_id, type, details})

  @impl true
  def init(state), do: {:ok, Map.put(state, :faults, [])}

  @impl true
  def handle_cast({:fault, drone_id, type, details}, state) do
    fault = %{drone_id: drone_id, type: type, details: details, at: DateTime.utc_now()}
    {:noreply, update_in(state, [:faults], &[fault | &1])}
  end
end

defmodule SDACS.RecoveryManager do
  use GenServer

  def start_link(_opts), do: GenServer.start_link(__MODULE__, %{}, name: __MODULE__)

  @impl true
  def init(state), do: {:ok, Map.put(state, :recoveries, 0)}

  @impl true
  def handle_cast({:recover, _drone_id}, state) do
    {:noreply, update_in(state, [:recoveries], &(&1 + 1))}
  end
end
