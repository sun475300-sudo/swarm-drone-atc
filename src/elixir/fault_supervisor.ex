defmodule SDACS.FaultSupervisor do
  @moduledoc """
  Phase 633 — Fault Supervisor (Elixir / OTP)

  드론 에이전트 프로세스를 감시하고 장애 발생 시 재시작하는
  OTP Supervisor 구현. one_for_one 전략을 사용한다.
  """

  use Supervisor

  @spec start_link(keyword()) :: Supervisor.on_start()
  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(opts) do
    n_drones = Keyword.get(opts, :n_drones, 10)

    children =
      for i <- 1..n_drones do
        drone_id = "D-#{String.pad_leading(Integer.to_string(i), 3, "0")}"
        Supervisor.child_spec(
          {SDACS.DroneAgent, drone_id: drone_id},
          id: String.to_atom("drone_#{i}")
        )
      end

    Supervisor.init(children, strategy: :one_for_one, max_restarts: 5, max_seconds: 10)
  end

  @doc "현재 감시 중인 드론 수를 반환한다."
  @spec drone_count() :: non_neg_integer()
  def drone_count do
    __MODULE__
    |> Supervisor.which_children()
    |> length()
  end
end

defmodule SDACS.DroneAgent do
  @moduledoc "개별 드론 에이전트 GenServer."
  use GenServer

  @spec start_link(keyword()) :: GenServer.on_start()
  def start_link(opts) do
    drone_id = Keyword.fetch!(opts, :drone_id)
    GenServer.start_link(__MODULE__, drone_id, name: {:global, drone_id})
  end

  @impl true
  def init(drone_id) do
    {:ok, %{id: drone_id, pos: {0.0, 0.0, 100.0}, vel: {0.0, 0.0, 0.0}, battery: 100.0}}
  end

  @impl true
  def handle_call(:state, _from, state), do: {:reply, state, state}

  @impl true
  def handle_cast({:update, pos, vel, battery}, state) do
    {:noreply, %{state | pos: pos, vel: vel, battery: battery}}
  end
end
