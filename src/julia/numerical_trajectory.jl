# Phase 554 — Numerical Trajectory Optimizer
# Julia module for computing optimal drone trajectories using numerical methods.

module NumericalTrajectory

export Waypoint, TrajectorySegment, TrajectoryOptimizer, optimize, smooth_trajectory

using LinearAlgebra

# ===== Data Structures =====

"""
    Waypoint

A single 3D waypoint in the trajectory with optional velocity constraints.
"""
struct Waypoint
    x::Float64
    y::Float64
    z::Float64
    vx::Float64   # desired velocity at this point
    vy::Float64
    vz::Float64
    t::Float64    # desired arrival time

    function Waypoint(x, y, z; vx=0.0, vy=0.0, vz=0.0, t=0.0)
        new(x, y, z, vx, vy, vz, t)
    end
end

# WP alias for brevity
const WP = Waypoint

"""
    TrajectorySegment

A segment between two waypoints with polynomial coefficients.
"""
struct TrajectorySegment
    wp_start::Waypoint
    wp_end::Waypoint
    duration::Float64
    coeffs_x::Vector{Float64}  # polynomial coefficients for x(t)
    coeffs_y::Vector{Float64}
    coeffs_z::Vector{Float64}
end

"""
    OptimizationResult

Result of a trajectory optimization run.
"""
struct OptimizationResult
    segments::Vector{TrajectorySegment}
    total_time::Float64
    total_distance::Float64
    iterations::Int
    converged::Bool
    cost::Float64
end

# ===== Utility Functions =====

"Euclidean distance between two waypoints"
function wp_distance(a::Waypoint, b::Waypoint)
    dx = b.x - a.x
    dy = b.y - a.y
    dz = b.z - a.z
    sqrt(dx^2 + dy^2 + dz^2)
end

"Generate cubic polynomial coefficients for interpolation between two boundary conditions"
function cubic_coefficients(p0, v0, p1, v1, T)
    # Solve: p(0)=p0, p'(0)=v0, p(T)=p1, p'(T)=v1
    # Coefficients: a0 + a1*t + a2*t^2 + a3*t^3
    a0 = p0
    a1 = v0
    T2, T3 = T^2, T^3
    a2 = (3*(p1-p0)/T2) - (2*v0 + v1)/T
    a3 = (-2*(p1-p0)/T3) + (v0 + v1)/T2
    [a0, a1, a2, a3]
end

"Evaluate polynomial at time t"
function poly_eval(coeffs, t)
    sum(coeffs[i+1] * t^i for i in 0:length(coeffs)-1)
end

# ===== Trajectory Optimizer =====

"""
    TrajectoryOptimizer

Numerical optimizer for drone trajectories through a series of waypoints.
Uses polynomial spline fitting with optional time allocation optimization.
"""
mutable struct TrajectoryOptimizer
    waypoints::Vector{Waypoint}
    max_velocity::Float64
    max_acceleration::Float64
    iterations::Int
    tolerance::Float64
    result::Union{OptimizationResult, Nothing}
end

function TrajectoryOptimizer(;
    max_velocity=15.0,
    max_acceleration=5.0,
    iterations=100,
    tolerance=1e-4
)
    TrajectoryOptimizer(Waypoint[], max_velocity, max_acceleration, iterations, tolerance, nothing)
end

"Add a waypoint to the optimizer"
function add_waypoint!(opt::TrajectoryOptimizer, wp::Waypoint)
    push!(opt.waypoints, wp)
end

"Compute initial time allocation based on distance and max velocity"
function initial_times(opt::TrajectoryOptimizer)
    n = length(opt.waypoints)
    times = Vector{Float64}(undef, n - 1)
    for i in 1:n-1
        d = wp_distance(opt.waypoints[i], opt.waypoints[i+1])
        times[i] = max(d / opt.max_velocity, 0.5)
    end
    times
end

"Build trajectory segments with cubic polynomial fitting"
function build_segments(wps::Vector{Waypoint}, times::Vector{Float64})
    segments = TrajectorySegment[]
    for i in 1:length(times)
        a = wps[i]
        b = wps[i+1]
        T = times[i]
        cx = cubic_coefficients(a.x, a.vx, b.x, b.vx, T)
        cy = cubic_coefficients(a.y, a.vy, b.y, b.vy, T)
        cz = cubic_coefficients(a.z, a.vz, b.z, b.vz, T)
        push!(segments, TrajectorySegment(a, b, T, cx, cy, cz))
    end
    segments
end

"Compute total path length by sampling segments"
function path_length(segments::Vector{TrajectorySegment}, samples=20)
    total = 0.0
    for seg in segments
        prev = (poly_eval(seg.coeffs_x, 0.0),
                poly_eval(seg.coeffs_y, 0.0),
                poly_eval(seg.coeffs_z, 0.0))
        for k in 1:samples
            t = seg.duration * k / samples
            curr = (poly_eval(seg.coeffs_x, t),
                    poly_eval(seg.coeffs_y, t),
                    poly_eval(seg.coeffs_z, t))
            dx, dy, dz = curr .- prev
            total += sqrt(dx^2 + dy^2 + dz^2)
            prev = curr
        end
    end
    total
end

"Optimize trajectory (gradient-descent-like time reallocation stub)"
function optimize(opt::TrajectoryOptimizer)
    isempty(opt.waypoints) && error("No waypoints added")
    length(opt.waypoints) < 2 && error("Need at least 2 waypoints")

    times = initial_times(opt)
    best_cost = Inf
    iters_done = 0
    converged = false

    for iter in 1:opt.iterations
        segs = build_segments(opt.waypoints, times)
        cost = sum(times)  # minimize total time

        if abs(best_cost - cost) < opt.tolerance
            converged = true
            break
        end

        # Simple gradient step: reduce each segment time slightly if feasible
        for i in eachindex(times)
            new_t = times[i] * 0.99
            d = wp_distance(opt.waypoints[i], opt.waypoints[i+1])
            min_t = d / opt.max_velocity
            times[i] = max(new_t, min_t)
        end

        best_cost = cost
        iters_done = iter
    end

    final_segs = build_segments(opt.waypoints, times)
    opt.result = OptimizationResult(
        final_segs,
        sum(times),
        path_length(final_segs),
        iters_done,
        converged,
        best_cost
    )
    opt.result
end

"Smooth trajectory by applying a moving average to waypoints"
function smooth_trajectory(wps::Vector{Waypoint}, window::Int=3)
    n = length(wps)
    smoothed = Vector{Waypoint}(undef, n)
    half = window ÷ 2
    for i in 1:n
        lo = max(1, i - half)
        hi = min(n, i + half)
        sx = mean(wps[j].x for j in lo:hi)
        sy = mean(wps[j].y for j in lo:hi)
        sz = mean(wps[j].z for j in lo:hi)
        smoothed[i] = Waypoint(sx, sy, sz; t=wps[i].t)
    end
    smoothed
end

end  # module

# ===== Main =====
using .NumericalTrajectory

println("Phase 554: Numerical Trajectory Optimizer")

waypoints = [
    WP(0.0,  0.0,  50.0),
    WP(20.0, 10.0, 60.0),
    WP(40.0, 5.0,  55.0),
    WP(60.0, 20.0, 65.0),
    WP(80.0, 0.0,  50.0),
]

opt = TrajectoryOptimizer(max_velocity=12.0, max_acceleration=4.0, iterations=50)
for wp in waypoints
    add_waypoint!(opt, wp)
end

result = optimize(opt)
println("Optimization converged: $(result.converged)")
println("Total time: $(round(result.total_time, digits=2))s")
println("Total distance: $(round(result.total_distance, digits=2))m")
println("Segments: $(length(result.segments))")
println("Cost: $(round(result.cost, digits=4))")
