# Phase 633 — Elixir OTP Fault Supervisor for Drone Agent Processes
defmodule SDACS.FaultSupervisor do
  use Supervisor

  def start_link(opts) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.DroneAgent, name: :drone_1},
      {SDACS.AirspaceController, name: :controller}
    ]
    Supervisor.init(children, strategy: :one_for_one, max_restarts: 5, max_seconds: 10)
  end
end

defmodule SDACS.DroneAgent do
  use GenServer
  def start_link(opts), do: GenServer.start_link(__MODULE__, %{}, opts)
  def init(state), do: {:ok, state}
end
