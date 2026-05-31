# Fault Supervisor — SDACS Phase 633
defmodule SDACS.FaultSupervisor do
  use Supervisor

  def start_link(opts) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def init(_opts) do
    children = []
    Supervisor.init(children, strategy: :one_for_one)
  end

  def drone_count, do: 0
end
