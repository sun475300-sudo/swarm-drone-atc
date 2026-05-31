defmodule Sdacs.FaultSupervisor do
  @moduledoc "OTP supervisor for SDACS drone fault tolerance"
  use Supervisor

  def start_link(opts) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {Sdacs.DroneWorker, id: "drone-001"},
      {Sdacs.TelemetryCollector, []}
    ]
    Supervisor.init(children, strategy: :one_for_one, max_restarts: 5, max_seconds: 60)
  end

  def list_drones do
    Supervisor.which_children(__MODULE__)
  end
end

defmodule Sdacs.DroneWorker do
  use GenServer

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts)
  end

  @impl true
  def init(opts) do
    {:ok, %{id: Keyword.get(opts, :id, "unknown"), status: :running}}
  end

  @impl true
  def handle_call(:status, _from, state) do
    {:reply, state.status, state}
  end
end
