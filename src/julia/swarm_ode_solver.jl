# SDACS Swarm ODE Solver — Julia
# 드론 군집 비행 동역학 수치 해석

module SwarmODESolver

using LinearAlgebra

export SwarmDynamics, solve_rk4, solve_euler, FlightState

"""드론 비행 상태"""
struct FlightState
    position::Vector{Float64}   # [x, y, z] m
    velocity::Vector{Float64}   # [vx, vy, vz] m/s
    time::Float64
end

"""군집 동역학 시스템"""
mutable struct SwarmDynamics
    n_drones::Int
    positions::Matrix{Float64}   # n×3
    velocities::Matrix{Float64}  # n×3
    masses::Vector{Float64}
    drag_coeff::Float64
    separation::Float64

    function SwarmDynamics(n::Int; mass=1.5, drag=0.1, sep=30.0)
        rng = MersenneTwister(42)
        pos = randn(rng, n, 3) .* 100.0
        vel = randn(rng, n, 3) .* 2.0
        new(n, pos, vel, fill(mass, n), drag, sep)
    end
end

"""인공 포텐셜 필드 가속도 계산"""
function compute_acceleration(sys::SwarmDynamics, i::Int)
    acc = zeros(3)
    for j in 1:sys.n_drones
        j == i && continue
        dr = sys.positions[j, :] - sys.positions[i, :]
        dist = norm(dr)
        dist < 1e-6 && continue

        # 반발력 (너무 가까우면)
        if dist < sys.separation
            acc -= (sys.separation / dist - 1.0) * dr / dist * 5.0
        end

        # 인력 (떼를 유지)
        if dist > sys.separation * 2
            acc += dr / dist * 0.5
        end
    end
    # 항력
    acc -= sys.drag_coeff * sys.velocities[i, :]
    return acc
end

"""4차 룽게-쿠타 적분"""
function solve_rk4(sys::SwarmDynamics, dt::Float64, steps::Int)
    history = FlightState[]

    for step in 1:steps
        push!(history, FlightState(
            copy(sys.positions[1, :]),
            copy(sys.velocities[1, :]),
            step * dt
        ))

        k1_v = zeros(sys.n_drones, 3)
        k1_p = copy(sys.velocities)

        for i in 1:sys.n_drones
            k1_v[i, :] = compute_acceleration(sys, i)
        end

        # 중간 상태로 sys 업데이트 (단순화된 RK4)
        for i in 1:sys.n_drones
            sys.velocities[i, :] += k1_v[i, :] * dt
            sys.positions[i, :] += k1_p[i, :] * dt
        end
    end
    return history
end

"""오일러 적분 (빠른 버전)"""
function solve_euler(sys::SwarmDynamics, dt::Float64, steps::Int)
    history = FlightState[]
    for step in 1:steps
        for i in 1:sys.n_drones
            acc = compute_acceleration(sys, i)
            sys.velocities[i, :] += acc * dt
            sys.positions[i, :] += sys.velocities[i, :] * dt
        end
        push!(history, FlightState(
            copy(sys.positions[1, :]),
            copy(sys.velocities[1, :]),
            step * dt
        ))
    end
    return history
end

"""분리 통계"""
function separation_stats(sys::SwarmDynamics)
    dists = Float64[]
    for i in 1:sys.n_drones
        for j in (i+1):sys.n_drones
            dr = sys.positions[i, :] - sys.positions[j, :]
            push!(dists, norm(dr))
        end
    end
    isempty(dists) && return (min=0.0, max=0.0, mean=0.0)
    return (min=minimum(dists), max=maximum(dists), mean=sum(dists)/length(dists))
end

end  # module
