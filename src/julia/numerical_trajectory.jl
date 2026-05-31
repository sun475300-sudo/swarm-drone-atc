# P554: NumericalTrajectory - Julia trajectory optimization
# Phase 554: Optimal path computation for drone swarms

module NumericalTrajectory

using LinearAlgebra

# Waypoint type for trajectory planning
struct Waypoint
    x::Float64
    y::Float64
    z::Float64
    speed::Float64
    heading::Float64
    timestamp::Float64
end

function Waypoint(; x=0.0, y=0.0, z=60.0, speed=10.0, heading=0.0, timestamp=0.0)
    Waypoint(x, y, z, speed, heading, timestamp)
end

# Trajectory segment between two waypoints
struct TrajectorySegment
    start_wp::Waypoint
    end_wp::Waypoint
    length::Float64
    duration::Float64
end

# 3D distance between waypoints
function distance(a::Waypoint, b::Waypoint)::Float64
    sqrt((b.x-a.x)^2 + (b.y-a.y)^2 + (b.z-a.z)^2)
end

# Create segment between two waypoints
function make_segment(a::Waypoint, b::Waypoint)::TrajectorySegment
    d = distance(a, b)
    avg_speed = (a.speed + b.speed) / 2.0
    dur = d / max(avg_speed, 0.1)
    TrajectorySegment(a, b, d, dur)
end

# Full trajectory
struct Trajectory
    waypoints::Vector{Waypoint}
    segments::Vector{TrajectorySegment}
    total_length::Float64
    total_duration::Float64
end

function build_trajectory(wps::Vector{Waypoint})::Trajectory
    segs = [make_segment(wps[i], wps[i+1]) for i in 1:length(wps)-1]
    tlen = sum(s.length for s in segs; init=0.0)
    tdur = sum(s.duration for s in segs; init=0.0)
    Trajectory(wps, segs, tlen, tdur)
end

# Simple optimization: minimize total length via waypoint reordering (greedy nearest neighbor)
function optimize(waypoints::Vector{Waypoint}, start_idx::Int=1)::Vector{Waypoint}
    remaining = collect(1:length(waypoints))
    ordered = [waypoints[start_idx]]
    deleteat!(remaining, findfirst(==(start_idx), remaining))

    current = waypoints[start_idx]
    while !isempty(remaining)
        nearest_i = argmin([distance(current, waypoints[j]) for j in remaining])
        next_wp = waypoints[remaining[nearest_i]]
        push!(ordered, next_wp)
        deleteat!(remaining, nearest_i)
        current = next_wp
    end
    ordered
end

# Interpolate position along trajectory at time t
function interpolate_position(traj::Trajectory, t::Float64)::Tuple{Float64,Float64,Float64}
    t_clamped = clamp(t, 0.0, traj.total_duration)
    elapsed = 0.0
    for seg in traj.segments
        if elapsed + seg.duration >= t_clamped
            frac = (t_clamped - elapsed) / max(seg.duration, 1e-9)
            s = seg.start_wp
            e = seg.end_wp
            return (
                s.x + frac*(e.x-s.x),
                s.y + frac*(e.y-s.y),
                s.z + frac*(e.z-s.z),
            )
        end
        elapsed += seg.duration
    end
    w = traj.waypoints[end]
    (w.x, w.y, w.z)
end

export Waypoint, TrajectorySegment, Trajectory, build_trajectory, optimize, interpolate_position, distance

end # module
