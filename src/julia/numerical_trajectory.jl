# Phase 554 — Julia Numerical Trajectory Optimization
# Waypoint path optimization using gradient descent for swarm drone ATC.

module NumericalTrajectory

using LinearAlgebra

# ── Waypoint type ─────────────────────────────────────────────────────────────

"""
    Waypoint

A single Waypoint in 3D space with an optional hold duration.
"""
struct Waypoint
    x::Float64        # East (m)
    y::Float64        # North (m)
    z::Float64        # Altitude AGL (m)
    hold_s::Float64   # Hover hold duration at this WP (seconds)
end

Waypoint(x, y, z) = Waypoint(x, y, z, 0.0)

# ── Path type ─────────────────────────────────────────────────────────────────

"""
    WaypointPath

Ordered list of Waypoint structs defining a drone's intended flight path.
Abbreviation WP is used throughout for brevity.
"""
struct WaypointPath
    drone_id::String
    waypoints::Vector{Waypoint}   # WP sequence
end

function total_length(path::WaypointPath)::Float64
    wps = path.waypoints
    sum(norm([wps[i+1].x - wps[i].x,
              wps[i+1].y - wps[i].y,
              wps[i+1].z - wps[i].z]) for i in 1:length(wps)-1; init=0.0)
end

# ── Cost function ─────────────────────────────────────────────────────────────

"""
    path_cost(waypoints; w_len, w_alt, w_smooth)

Composite cost:
- `w_len`    : weight on total path length (minimize)
- `w_alt`    : weight on altitude variation penalty (prefer stable altitude)
- `w_smooth` : weight on heading change penalty (minimize sharp turns)
"""
function path_cost(waypoints::Vector{Waypoint};
                   w_len::Float64    = 1.0,
                   w_alt::Float64    = 0.5,
                   w_smooth::Float64 = 0.3)::Float64
    n = length(waypoints)
    n < 2 && return 0.0

    len_cost   = 0.0
    alt_cost   = 0.0
    smooth_cost = 0.0

    for i in 1:n-1
        dx = waypoints[i+1].x - waypoints[i].x
        dy = waypoints[i+1].y - waypoints[i].y
        dz = waypoints[i+1].z - waypoints[i].z
        seg_len = sqrt(dx^2 + dy^2 + dz^2)
        len_cost  += seg_len
        alt_cost  += dz^2
    end

    for i in 2:n-1
        v1 = [waypoints[i].x   - waypoints[i-1].x,
              waypoints[i].y   - waypoints[i-1].y]
        v2 = [waypoints[i+1].x - waypoints[i].x,
              waypoints[i+1].y - waypoints[i].y]
        n1, n2 = norm(v1), norm(v2)
        if n1 > 1e-9 && n2 > 1e-9
            cos_a = clamp(dot(v1, v2) / (n1 * n2), -1.0, 1.0)
            smooth_cost += (1.0 - cos_a)
        end
    end

    w_len * len_cost + w_alt * alt_cost + w_smooth * smooth_cost
end

# ── Numerical gradient ────────────────────────────────────────────────────────

function numerical_gradient(waypoints::Vector{Waypoint}, idx::Int;
                             eps::Float64 = 1e-4)::NTuple{3, Float64}
    wp = waypoints[idx]
    base_cost = path_cost(waypoints)

    # Perturb x
    wp_px = Waypoint(wp.x + eps, wp.y, wp.z, wp.hold_s)
    wps_px = copy(waypoints); wps_px[idx] = wp_px
    grad_x = (path_cost(wps_px) - base_cost) / eps

    # Perturb y
    wp_py = Waypoint(wp.x, wp.y + eps, wp.z, wp.hold_s)
    wps_py = copy(waypoints); wps_py[idx] = wp_py
    grad_y = (path_cost(wps_py) - base_cost) / eps

    # Perturb z
    wp_pz = Waypoint(wp.x, wp.y, wp.z + eps, wp.hold_s)
    wps_pz = copy(waypoints); wps_pz[idx] = wp_pz
    grad_z = (path_cost(wps_pz) - base_cost) / eps

    (grad_x, grad_y, grad_z)
end

# ── Gradient descent optimizer ────────────────────────────────────────────────

"""
    optimize(path; lr, max_iter, tol, fix_endpoints) -> WaypointPath

Gradient-descent path optimizer for a WaypointPath.
Intermediate WP positions are updated; endpoints are held fixed by default.

Returns an optimized WaypointPath.  Phase 554 core routine.
"""
function optimize(path::WaypointPath;
                  lr::Float64            = 0.5,
                  max_iter::Int          = 200,
                  tol::Float64           = 1e-5,
                  fix_endpoints::Bool    = true)::WaypointPath

    wps = copy(path.waypoints)
    n   = length(wps)

    start_idx = fix_endpoints ? 2 : 1
    end_idx   = fix_endpoints ? n - 1 : n

    prev_cost = path_cost(wps)

    for iter in 1:max_iter
        for idx in start_idx:end_idx
            gx, gy, gz = numerical_gradient(wps, idx)
            wp = wps[idx]
            wps[idx] = Waypoint(wp.x - lr * gx,
                                wp.y - lr * gy,
                                wp.z - lr * gz,
                                wp.hold_s)
        end

        curr_cost = path_cost(wps)
        delta     = abs(prev_cost - curr_cost)

        if iter % 50 == 0
            @info "[554] optimize iter=$iter cost=$(round(curr_cost; digits=4))"
        end

        delta < tol && break
        prev_cost = curr_cost
    end

    WaypointPath(path.drone_id, wps)
end

# ── Demo / entry point ────────────────────────────────────────────────────────

function demo()
    println("[554] NumericalTrajectory — Phase 554 demo")

    # Build an initial zigzag WP path
    initial_wps = [
        Waypoint(0.0,   0.0,  20.0),   # WP 1 — fixed start
        Waypoint(25.0, 30.0,  25.0),   # WP 2 — intermediate (will be optimized)
        Waypoint(50.0, 10.0,  30.0),   # WP 3 — intermediate
        Waypoint(75.0, 40.0,  22.0),   # WP 4 — intermediate
        Waypoint(100.0, 0.0,  20.0),   # WP 5 — fixed end
    ]

    raw_path = WaypointPath("DRONE-554", initial_wps)
    println("  Initial path length : $(round(total_length(raw_path); digits=2)) m")
    println("  Initial cost        : $(round(path_cost(raw_path.waypoints); digits=4))")

    opt_path = optimize(raw_path; lr=0.4, max_iter=300, tol=1e-6)
    println("  Optimized length    : $(round(total_length(opt_path); digits=2)) m")
    println("  Optimized cost      : $(round(path_cost(opt_path.waypoints); digits=4))")

    println("[554] Optimized Waypoints:")
    for (i, wp) in enumerate(opt_path.waypoints)
        @printf("  WP%d  x=%.2f  y=%.2f  z=%.2f\n", i, wp.x, wp.y, wp.z)
    end
end

end  # module NumericalTrajectory

# Run demo when executed directly
NumericalTrajectory.demo()
