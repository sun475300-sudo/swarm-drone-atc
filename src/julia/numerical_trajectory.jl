# Phase 554: Numerical Trajectory — 드론 궤적 수치 최적화 (Julia)
# Runge-Kutta based numerical trajectory optimization for drone waypoints.

module NumericalTrajectory

export Waypoint, TrajectoryState, optimize_trajectory, rk4_step

using LinearAlgebra

# Phase marker
const PHASE = 554

"""
Waypoint represents a 3D target position with constraints.
"""
struct Waypoint
    id   :: Int
    x    :: Float64
    y    :: Float64
    z    :: Float64
    vmax :: Float64   # max velocity at this WP (m/s)
    tol  :: Float64   # arrival tolerance (m)
end

"""
TrajectoryState captures the drone's kinematic state.
"""
mutable struct TrajectoryState
    x  :: Float64
    y  :: Float64
    z  :: Float64
    vx :: Float64
    vy :: Float64
    vz :: Float64
end

"""
    rk4_step(state, f, dt) -> TrajectoryState
Fourth-order Runge-Kutta integration step.
"""
function rk4_step(s::TrajectoryState, f::Function, dt::Float64)::TrajectoryState
    q  = [s.x, s.y, s.z, s.vx, s.vy, s.vz]
    k1 = f(q)
    k2 = f(q .+ (dt/2) .* k1)
    k3 = f(q .+ (dt/2) .* k2)
    k4 = f(q .+ dt      .* k3)
    q_next = q .+ (dt/6) .* (k1 .+ 2k2 .+ 2k3 .+ k4)
    return TrajectoryState(q_next[1], q_next[2], q_next[3],
                           q_next[4], q_next[5], q_next[6])
end

"""
    build_dynamics(wp) -> Function
Returns a dynamics function steering toward waypoint `wp`.
"""
function build_dynamics(wp::Waypoint, k_p::Float64=0.5, k_d::Float64=0.3)
    return function(q)
        pos = q[1:3]; vel = q[4:6]
        target = [wp.x, wp.y, wp.z]
        err    = target .- pos
        # PD controller on position error
        acc    = k_p .* err .- k_d .* vel
        # Clamp acceleration
        a_norm = norm(acc)
        if a_norm > 5.0
            acc = acc .* (5.0 / a_norm)
        end
        return [vel[1], vel[2], vel[3], acc[1], acc[2], acc[3]]
    end
end

"""
    optimize_trajectory(waypoints, dt, max_steps) -> Vector{TrajectoryState}
Simulate and optimize trajectory through a list of Waypoints using RK4.
"""
function optimize_trajectory(waypoints::Vector{Waypoint}, dt::Float64=0.1,
                              max_steps::Int=200)::Vector{TrajectoryState}
    state = TrajectoryState(0.0, 0.0, 30.0, 0.0, 0.0, 0.0)
    history = TrajectoryState[]
    push!(history, deepcopy(state))

    for wp in waypoints
        dyn = build_dynamics(wp)
        for _ in 1:max_steps
            state = rk4_step(state, dyn, dt)
            push!(history, deepcopy(state))
            dist = sqrt((state.x - wp.x)^2 + (state.y - wp.y)^2 + (state.z - wp.z)^2)
            if dist < wp.tol
                break
            end
        end
    end
    return history
end

"""
    path_length(history) -> Float64
Compute total path arc-length from trajectory history.
"""
function path_length(history::Vector{TrajectoryState})::Float64
    total = 0.0
    for i in 2:length(history)
        dx = history[i].x - history[i-1].x
        dy = history[i].y - history[i-1].y
        dz = history[i].z - history[i-1].z
        total += sqrt(dx^2 + dy^2 + dz^2)
    end
    return total
end

end # module

# ── Run demo ──────────────────────────────────────────────────────
using .NumericalTrajectory

waypoints = [
    Waypoint(1, 50.0, 0.0, 30.0, 10.0, 2.0),
    Waypoint(2, 50.0, 50.0, 40.0, 8.0, 2.0),
    Waypoint(3, 0.0, 50.0, 30.0, 5.0, 2.0),
]
traj = optimize_trajectory(waypoints)
len  = path_length(traj)
println("Phase $(NumericalTrajectory.PHASE): steps=$(length(traj)), path_length=$(round(len, digits=2))m")
