# SDACS Numerical Trajectory Optimizer — Julia (Phase 554)
# 드론 군집 경로 최적화 (수치해석 기반)

module NumericalTrajectory

export Waypoint, TrajectorySegment, optimize_trajectory, smooth_path

# Phase 554 — Waypoint 타입
struct Waypoint
    x::Float64
    y::Float64
    z::Float64
    speed::Float64      # m/s
    heading::Float64    # radians
end

struct TrajectorySegment
    wp_start::Waypoint
    wp_end::Waypoint
    duration::Float64   # seconds
    length::Float64     # meters
end

function distance(a::Waypoint, b::Waypoint)
    sqrt((a.x - b.x)^2 + (a.y - b.y)^2 + (a.z - b.z)^2)
end

function segment_duration(a::Waypoint, b::Waypoint, max_speed::Float64 = 15.0)
    d = distance(a, b)
    spd = min(a.speed, max_speed)
    spd < 1e-6 ? Inf : d / spd
end

function build_trajectory(waypoints::Vector{Waypoint})
    segs = TrajectorySegment[]
    for i in 1:length(waypoints)-1
        a, b = waypoints[i], waypoints[i+1]
        d = distance(a, b)
        dt = segment_duration(a, b)
        push!(segs, TrajectorySegment(a, b, dt, d))
    end
    segs
end

# WP 경로 최적화 (가장 가까운 이웃 휴리스틱)
function optimize_trajectory(waypoints::Vector{Waypoint}; seed::Int=42)
    isempty(waypoints) && return waypoints
    rng = MersenneTwister(seed)
    
    unvisited = copy(waypoints)
    path = Waypoint[]
    current = popfirst!(unvisited)
    push!(path, current)
    
    while !isempty(unvisited)
        idx = argmin([distance(current, wp) for wp in unvisited])
        current = unvisited[idx]
        push!(path, current)
        deleteat!(unvisited, idx)
    end
    path
end

# 3차 스플라인 경로 평활화
function smooth_path(waypoints::Vector{Waypoint}, steps_per_segment::Int = 10)
    isempty(waypoints) && return waypoints
    length(waypoints) == 1 && return waypoints
    
    smoothed = Waypoint[]
    for i in 1:length(waypoints)-1
        a, b = waypoints[i], waypoints[i+1]
        for t in range(0.0, 1.0, length=steps_per_segment)
            # 선형 보간 (단순화된 경로 평활화)
            x = a.x * (1-t) + b.x * t
            y = a.y * (1-t) + b.y * t
            z = a.z * (1-t) + b.z * t
            spd = a.speed * (1-t) + b.speed * t
            push!(smoothed, Waypoint(x, y, z, spd, atan(b.y-a.y, b.x-a.x)))
        end
    end
    push!(smoothed, last(waypoints))
    smoothed
end

function total_path_length(waypoints::Vector{Waypoint})
    sum(distance(waypoints[i], waypoints[i+1]) for i in 1:length(waypoints)-1; init=0.0)
end

function total_flight_time(waypoints::Vector{Waypoint})
    sum(segment_duration(waypoints[i], waypoints[i+1]) for i in 1:length(waypoints)-1; init=0.0)
end

end  # module
