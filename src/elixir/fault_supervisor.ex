defmodule SDACS.FaultSupervisor do
  @moduledoc """
  Phase 633 — Elixir OTP Fault Supervisor for drone agent processes.
  Supervises drone worker processes with one-for-one restart strategy.
  """
  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {SDACS.DroneWorker, id: :primary},
    ]
    Supervisor.init(children, strategy: :one_for_one, max_restarts: 3, max_seconds: 5)
  end
end

defmodule SDACS.DroneWorker do
  @moduledoc "GenServer drone agent managed by FaultSupervisor."
  use GenServer

  def start_link(opts), do: GenServer.start_link(__MODULE__, opts)

  @impl true
  def init(opts), do: {:ok, %{id: Keyword.get(opts, :id, :unknown), status: :active}}

  @impl true
  def handle_call(:status, _from, state), do: {:reply, state.status, state}
end
