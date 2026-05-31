# Phase 633 — Swarm Fault Supervisor (OTP) in Elixir
defmodule SDACS.FaultSupervisor do
  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.DroneMonitor, []},
      {SDACS.ConflictResolver, []},
      {SDACS.TelemetryCollector, []}
    ]
    Supervisor.init(children, strategy: :one_for_one, max_restarts: 10, max_seconds: 60)
  end
end

defmodule SDACS.DroneMonitor do
  use GenServer
  def start_link(_), do: GenServer.start_link(__MODULE__, %{}, name: __MODULE__)
  def init(state), do: {:ok, state}
  def handle_call({:status, id}, _from, state), do: {:reply, Map.get(state, id, :unknown), state}
end
