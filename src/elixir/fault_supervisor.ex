# P633: Fault Supervisor - Elixir stub
# Supervises drone fault detection and recovery processes

defmodule SDACS.FaultSupervisor do
  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.FaultDetector, []},
      {SDACS.RecoveryManager, []}
    ]
    Supervisor.init(children, strategy: :one_for_one)
  end

  def report_fault(drone_id, fault_type) do
    GenServer.cast(SDACS.FaultDetector, {:fault, drone_id, fault_type})
  end
end

defmodule SDACS.FaultDetector do
  use GenServer

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{faults: []}, name: __MODULE__)
  end

  @impl true
  def init(state), do: {:ok, state}

  @impl true
  def handle_cast({:fault, drone_id, fault_type}, state) do
    {:noreply, %{state | faults: [{drone_id, fault_type} | state.faults]}}
  end
end

defmodule SDACS.RecoveryManager do
  use GenServer

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, %{}, name: __MODULE__)
  end

  @impl true
  def init(state), do: {:ok, state}
end
