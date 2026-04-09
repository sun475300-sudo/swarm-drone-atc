# Phase 556: Elixir Distributed Supervisor Tree
# OTP Supervisor 패턴으로 드론 프로세스 감시 및 자동 재시작

defmodule SwarmSupervisor do
  @moduledoc "군집 드론 감시 트리 - 장애 감지 및 자동 복구"

  defmodule PRNG do
    defstruct state: 0

    def new(seed) do
      %PRNG{state: Bitwise.bxor(seed, 0x6C62272E)}
    end

    def next(%PRNG{state: s} = rng) do
      s1 = Bitwise.bxor(s, Bitwise.bsl(s, 13))
      s2 = Bitwise.bxor(s1, Bitwise.bsr(s1, 7))
      s3 = Bitwise.bxor(s2, Bitwise.bsl(s2, 17))
      {abs(s3), %{rng | state: s3}}
    end

    def uniform(rng) do
      {val, rng} = next(rng)
      {rem(val, 10000) / 10000.0, rng}
    end
  end

  defmodule DroneProcess do
    defstruct [
      :id, :status, :restarts, :uptime, :health,
      crashes: 0, messages_handled: 0
    ]

    def new(id) do
      %DroneProcess{
        id: id, status: :running, restarts: 0,
        uptime: 0, health: 1.0, crashes: 0,
        messages_handled: 0
      }
    end

    def tick(drone) do
      %{drone | uptime: drone.uptime + 1,
                messages_handled: drone.messages_handled + 1}
    end

    def crash(drone) do
      %{drone | status: :crashed, crashes: drone.crashes + 1, health: 0.0}
    end

    def restart(drone) do
      %{drone | status: :running, restarts: drone.restarts + 1, health: 0.8}
    end
  end

  defmodule Supervisor do
    defstruct [:strategy, :children, :max_restarts, :total_restarts, :events]

    def new(strategy \\ :one_for_one, max_restarts \\ 5) do
      %Supervisor{
        strategy: strategy, children: %{},
        max_restarts: max_restarts, total_restarts: 0,
        events: []
      }
    end

    def add_child(sup, child_id, child) do
      %{sup | children: Map.put(sup.children, child_id, child)}
    end

    def handle_crash(sup, child_id) do
      case sup.strategy do
        :one_for_one ->
          child = Map.get(sup.children, child_id)
          if child && sup.total_restarts < sup.max_restarts * map_size(sup.children) do
            restarted = DroneProcess.restart(child)
            event = "Restarted #{child_id} (strategy: one_for_one)"
            %{sup |
              children: Map.put(sup.children, child_id, restarted),
              total_restarts: sup.total_restarts + 1,
              events: [event | sup.events]}
          else
            event = "Max restarts exceeded for #{child_id}"
            %{sup | events: [event | sup.events]}
          end

        :one_for_all ->
          restarted_children = Enum.reduce(sup.children, %{}, fn {id, child}, acc ->
            Map.put(acc, id, DroneProcess.restart(child))
          end)
          event = "Restarted all children (strategy: one_for_all)"
          %{sup |
            children: restarted_children,
            total_restarts: sup.total_restarts + map_size(sup.children),
            events: [event | sup.events]}

        _ -> sup
      end
    end

    def tick_all(sup) do
      updated = Enum.reduce(sup.children, %{}, fn {id, child}, acc ->
        case child.status do
          :running -> Map.put(acc, id, DroneProcess.tick(child))
          _ -> Map.put(acc, id, child)
        end
      end)
      %{sup | children: updated}
    end
  end

  def run_simulation(n_drones, n_steps, seed) do
    rng = PRNG.new(seed)
    sup = Supervisor.new(:one_for_one, 3)

    # Add drone processes
    sup = Enum.reduce(0..(n_drones - 1), sup, fn i, acc ->
      Supervisor.add_child(acc, "drone_#{i}", DroneProcess.new("drone_#{i}"))
    end)

    # Run steps
    {sup, rng, _} = Enum.reduce(1..n_steps, {sup, rng, 0}, fn _step, {sup, rng, crashes} ->
      sup = Supervisor.tick_all(sup)

      # Random crash
      {val, rng} = PRNG.uniform(rng)
      if val < 0.1 do
        drone_ids = Map.keys(sup.children)
        {idx, rng} = PRNG.next(rng)
        target = Enum.at(drone_ids, rem(abs(idx), length(drone_ids)))
        child = Map.get(sup.children, target)
        if child.status == :running do
          crashed = DroneProcess.crash(child)
          sup = %{sup | children: Map.put(sup.children, target, crashed)}
          sup = Supervisor.handle_crash(sup, target)
          {sup, rng, crashes + 1}
        else
          {sup, rng, crashes}
        end
      else
        {sup, rng, crashes}
      end
    end)

    # Summary
    running = Enum.count(sup.children, fn {_, c} -> c.status == :running end)
    total_crashes = Enum.reduce(sup.children, 0, fn {_, c}, acc -> acc + c.crashes end)

    %{
      drones: n_drones,
      running: running,
      total_restarts: sup.total_restarts,
      total_crashes: total_crashes,
      events: length(sup.events)
    }
  end
end

# Main
result = SwarmSupervisor.run_simulation(10, 30, 42)
IO.inspect(result, label: "Supervisor Tree Result")
