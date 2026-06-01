defmodule SDACS.SupervisorTree do
  @moduledoc """
  Phase 556: Supervisor Tree — 군집 드론 OTP 수퍼바이저 트리 (Elixir)
  OTP supervision tree with restart strategies for drone fleet resilience.
  """

  use Supervisor

  @phase 556

  # ── Root Supervisor ────────────────────────────────────────────

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl Supervisor
  def init(_opts) do
    children = [
      {SDACS.TelemetryWorker, name: :telemetry_worker},
      {SDACS.FlightController, name: :flight_controller},
      {SDACS.ConflictResolver, name: :conflict_resolver},
      {SDACS.MissionPlanner, name: :mission_planner},
    ]

    # :one_for_one — restart only the failed child
    Supervisor.init(children, strategy: :one_for_one, max_restarts: 5, max_seconds: 10)
  end

  def phase, do: @phase
end

defmodule SDACS.TelemetryWorker do
  @moduledoc "Handles drone telemetry ingestion and forwarding."
  use GenServer

  def start_link(opts), do: GenServer.start_link(__MODULE__, %{}, opts)

  @impl GenServer
  def init(state) do
    schedule_poll()
    {:ok, Map.put(state, :count, 0)}
  end

  @impl GenServer
  def handle_info(:poll, state) do
    schedule_poll()
    {:noreply, Map.update!(state, :count, &(&1 + 1))}
  end

  defp schedule_poll, do: Process.send_after(self(), :poll, 100)
end

defmodule SDACS.FlightController do
  @moduledoc "Issues flight commands to the drone fleet."
  use GenServer

  def start_link(opts), do: GenServer.start_link(__MODULE__, %{drones: []}, opts)

  @impl GenServer
  def init(state), do: {:ok, state}

  @impl GenServer
  def handle_call({:command, drone_id, cmd}, _from, state) do
    # Validate and queue command
    {:reply, {:ok, drone_id, cmd}, state}
  end
end

defmodule SDACS.ConflictResolver do
  @moduledoc "Detects and resolves airspace conflicts between drones."
  use GenServer

  def start_link(opts), do: GenServer.start_link(__MODULE__, %{conflicts: []}, opts)

  @impl GenServer
  def init(state), do: {:ok, state}

  @impl GenServer
  def handle_cast({:check_conflict, d1, d2, dist}, state) do
    if dist < 5.0 do
      entry = {d1, d2, :separation_violation}
      {:noreply, Map.update!(state, :conflicts, &[entry | &1])}
    else
      {:noreply, state}
    end
  end

  @impl GenServer
  def handle_call(:get_conflicts, _from, state) do
    {:reply, state.conflicts, state}
  end
end

defmodule SDACS.MissionPlanner do
  @moduledoc "Assigns and tracks missions for each drone."
  use GenServer

  def start_link(opts), do: GenServer.start_link(__MODULE__, %{missions: %{}}, opts)

  @impl GenServer
  def init(state), do: {:ok, state}

  @impl GenServer
  def handle_call({:assign, drone_id, mission}, _from, state) do
    new_state = put_in(state, [:missions, drone_id], mission)
    {:reply, :ok, new_state}
  end

  @impl GenServer
  def handle_call({:status, drone_id}, _from, state) do
    {:reply, Map.get(state.missions, drone_id, :unassigned), state}
  end
end

# ── Restart strategy documentation ────────────────────────────────
# :one_for_one  — restart only failed child
# :one_for_all  — restart all children when one fails
# :rest_for_one — restart failed child and all children started after it
#
# Phase 556 implements :one_for_one for maximum fault isolation.
