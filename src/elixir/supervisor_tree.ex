defmodule Sdacs.SupervisorTree do
  @moduledoc """
  SDACS supervisor tree for drone fleet management (Phase 556).
  OTP-based supervision with fault-tolerant restart strategies.
  """
  use Supervisor

  @max_restarts 5
  @max_seconds  60

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(opts) do
    fleet_size = Keyword.get(opts, :fleet_size, 5)

    children = [
      # Telemetry collector with permanent restart
      %{
        id:       Sdacs.TelemetryCollector,
        start:    {Sdacs.TelemetryCollector, :start_link, [[]]},
        restart:  :permanent,
        shutdown: 5000,
        type:     :worker
      },
      # Mission controller with transient restart
      %{
        id:       Sdacs.MissionController,
        start:    {Sdacs.MissionController, :start_link, [[]]},
        restart:  :transient,
        shutdown: 10000,
        type:     :worker
      },
      # Dynamic supervisor for drone workers
      {DynamicSupervisor, name: Sdacs.DroneSupervisor, strategy: :one_for_one}
    ]

    Supervisor.init(children,
      strategy:   :one_for_one,
      max_restarts: @max_restarts,
      max_seconds:  @max_seconds
    )
  end

  # Start a drone worker under dynamic supervisor
  def start_drone(drone_id) do
    spec = %{
      id:      {:drone, drone_id},
      start:   {Sdacs.DroneWorker, :start_link, [[id: drone_id]]},
      restart: :temporary,
      type:    :worker
    }
    DynamicSupervisor.start_child(Sdacs.DroneSupervisor, spec)
  end

  # Stop a drone worker
  def stop_drone(drone_id) do
    case Registry.lookup(Sdacs.DroneRegistry, drone_id) do
      [{pid, _}] -> DynamicSupervisor.terminate_child(Sdacs.DroneSupervisor, pid)
      []         -> {:error, :not_found}
    end
  end

  # Get supervisor tree status
  def tree_status do
    children = Supervisor.which_children(__MODULE__)
    drone_children = DynamicSupervisor.which_children(Sdacs.DroneSupervisor)

    %{
      top_level_children: length(children),
      active_drones:      length(drone_children),
      supervisor:         __MODULE__,
      strategy:           :one_for_one
    }
  end

  # Restart a specific component
  def restart_component(component_id) do
    Supervisor.terminate_child(__MODULE__, component_id)
    Supervisor.restart_child(__MODULE__, component_id)
  end
end
