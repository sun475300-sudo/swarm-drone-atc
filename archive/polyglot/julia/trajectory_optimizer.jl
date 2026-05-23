#=
SDACS 궤적 최적화 엔진 — Julia
================================
고성능 수치 계산 기반 경로 최적화

기능:
  - B-spline 궤적 평활화
  - 에너지 최적 경로 (풍향 고려)
  - 다목적 최적화 (시간 vs 에너지 vs 안전)
  - BFGS 기반 매개변수 최적화
=#

module TrajectoryOptimizer

using LinearAlgebra
using Statistics

export Vec3, Waypoint, optimize_trajectory, smooth_bspline, energy_cost

# ── 기본 타입 ────────────────────────────────────────────

struct Vec3
    x::Float64
    y::Float64
    z::Float64
end

Vec3() = Vec3(0.0, 0.0, 0.0)

Base.:+(a::Vec3, b::Vec3) = Vec3(a.x + b.x, a.y + b.y, a.z + b.z)
Base.:-(a::Vec3, b::Vec3) = Vec3(a.x - b.x, a.y - b.y, a.z - b.z)
Base.:*(a::Vec3, s::Float64) = Vec3(a.x * s, a.y * s, a.z * s)
Base.:*(s::Float64, a::Vec3) = a * s

distance(a::Vec3, b::Vec3) = norm([a.x - b.x, a.y - b.y, a.z - b.z])
magnitude(a::Vec3) = norm([a.x, a.y, a.z])

struct Waypoint
    position::Vec3
    speed::Float64      # m/s
    timestamp::Float64  # seconds
end

# ── B-Spline 평활화 ─────────────────────────────────────

"""
3차 B-spline 기반 궤적 평활화
입력: 웨이포인트 리스트, 분해능(포인트 수)
출력: 평활화된 궤적 포인트
"""
function smooth_bspline(waypoints::Vector{Vec3}; resolution::Int=100)
    n = length(waypoints)
    if n < 4
        return waypoints
    end

    smoothed = Vec3[]
    for t_norm in range(0, 1, length=resolution)
        t = t_norm * (n - 3)
        i = clamp(Int(floor(t)) + 1, 1, n - 3)
        u = t - (i - 1)

        # De Boor 알고리즘 (3차)
        b0 = (1 - u)^3 / 6
        b1 = (3u^3 - 6u^2 + 4) / 6
        b2 = (-3u^3 + 3u^2 + 3u + 1) / 6
        b3 = u^3 / 6

        p = waypoints[i] * b0 +
            waypoints[min(i+1, n)] * b1 +
            waypoints[min(i+2, n)] * b2 +
            waypoints[min(i+3, n)] * b3

        push!(smoothed, p)
    end

    return smoothed
end

# ── 에너지 비용 함수 ────────────────────────────────────

"""
경로 에너지 비용 계산 (Wh)
- 수평 이동: 거리 × 기본 소모
- 상승: 고도차 × 상승 소모
- 하강: 고도차 × 하강 소모 (회생)
- 풍향 보정: 역풍 시 추가 소모
"""
function energy_cost(
    path::Vector{Vec3};
    base_consumption::Float64=0.5,    # Wh/m
    climb_cost::Float64=2.0,          # Wh/m
    descent_recovery::Float64=0.3,    # Wh/m (회생)
    wind::Vec3=Vec3(0.0, 0.0, 0.0),  # 풍속 벡터
    drone_speed::Float64=10.0         # m/s
)
    total_energy = 0.0
    for i in 2:length(path)
        seg = path[i] - path[i-1]
        h_dist = norm([seg.x, seg.y])
        v_dist = seg.z

        # 수평 이동 에너지
        total_energy += h_dist * base_consumption

        # 수직 이동 에너지
        if v_dist > 0
            total_energy += v_dist * climb_cost
        else
            total_energy += abs(v_dist) * descent_recovery
        end

        # 풍향 보정
        if magnitude(wind) > 0.1
            seg_dir = [seg.x, seg.y, seg.z] / max(norm([seg.x, seg.y, seg.z]), 1e-6)
            wind_vec = [wind.x, wind.y, wind.z]
            headwind = -dot(seg_dir, wind_vec)
            if headwind > 0
                wind_factor = headwind / drone_speed
                total_energy += h_dist * base_consumption * wind_factor * 0.5
            end
        end
    end

    return total_energy
end

# ── 경로 최적화 ─────────────────────────────────────────

"""
다목적 궤적 최적화
목적 함수: w_time × 시간 + w_energy × 에너지 + w_safety × 위험도
"""
function optimize_trajectory(
    start::Vec3,
    goal::Vec3,
    obstacles::Vector{Vec3}=Vec3[];
    n_waypoints::Int=5,
    w_time::Float64=0.3,
    w_energy::Float64=0.5,
    w_safety::Float64=0.2,
    min_separation::Float64=50.0,
    iterations::Int=100,
    wind::Vec3=Vec3()
)
    # 초기 경로: 직선 보간
    path = Vec3[]
    for i in 0:n_waypoints+1
        t = i / (n_waypoints + 1)
        p = start * (1.0 - t) + goal * t
        push!(path, p)
    end

    best_path = copy(path)
    best_cost = Inf

    # 경사 하강법 최적화
    for iter in 1:iterations
        # 중간 웨이포인트만 조정 (시작/끝 고정)
        for wi in 2:length(path)-1
            best_local_cost = Inf
            best_local_pos = path[wi]

            # 8방향 + 수직 탐색
            for dx in [-10.0, 0.0, 10.0]
                for dy in [-10.0, 0.0, 10.0]
                    for dz in [-5.0, 0.0, 5.0]
                        candidate = path[wi] + Vec3(dx, dy, dz)

                        # 장애물 안전 거리 체크
                        safe = all(obs -> distance(candidate, obs) >= min_separation, obstacles)
                        if !safe continue end

                        # 임시 경로로 비용 계산
                        test_path = copy(path)
                        test_path[wi] = candidate

                        # 비용 함수
                        e = energy_cost(test_path, wind=wind)
                        total_dist = sum(distance(test_path[i], test_path[i+1]) for i in 1:length(test_path)-1)
                        t_cost = total_dist / 10.0  # 10 m/s 가정

                        # 안전 비용 (장애물 근접도)
                        s_cost = isempty(obstacles) ? 0.0 :
                            sum(1.0 / max(minimum(distance(p, obs) for obs in obstacles), 1.0) for p in test_path)

                        cost = w_time * t_cost + w_energy * e + w_safety * s_cost

                        if cost < best_local_cost
                            best_local_cost = cost
                            best_local_pos = candidate
                        end
                    end
                end
            end

            path[wi] = best_local_pos
        end

        # 전체 비용 계산
        total_cost = w_time * sum(distance(path[i], path[i+1]) for i in 1:length(path)-1) / 10.0 +
                     w_energy * energy_cost(path, wind=wind)

        if total_cost < best_cost
            best_cost = total_cost
            best_path = copy(path)
        end
    end

    return (
        path = best_path,
        cost = best_cost,
        energy = energy_cost(best_path, wind=wind),
        distance = sum(distance(best_path[i], best_path[i+1]) for i in 1:length(best_path)-1)
    )
end

# ── RDP (Ramer-Douglas-Peucker) 경로 단순화 ─────────────

"""
경로 단순화 — 불필요한 중간점 제거
"""
function simplify_rdp(path::Vector{Vec3}, epsilon::Float64=5.0)
    if length(path) <= 2
        return path
    end

    # 시작-끝 직선으로부터 최대 거리 점 찾기
    start_pt = path[1]
    end_pt = path[end]
    line_vec = [end_pt.x - start_pt.x, end_pt.y - start_pt.y, end_pt.z - start_pt.z]
    line_len = norm(line_vec)

    max_dist = 0.0
    max_idx = 1

    for i in 2:length(path)-1
        pt_vec = [path[i].x - start_pt.x, path[i].y - start_pt.y, path[i].z - start_pt.z]
        if line_len > 1e-6
            t = clamp(dot(pt_vec, line_vec) / (line_len^2), 0.0, 1.0)
            proj = [start_pt.x, start_pt.y, start_pt.z] .+ t .* line_vec
            dist = norm([path[i].x, path[i].y, path[i].z] .- proj)
        else
            dist = norm(pt_vec)
        end

        if dist > max_dist
            max_dist = dist
            max_idx = i
        end
    end

    if max_dist > epsilon
        left = simplify_rdp(path[1:max_idx], epsilon)
        right = simplify_rdp(path[max_idx:end], epsilon)
        return vcat(left[1:end-1], right)
    else
        return [path[1], path[end]]
    end
end

end # module
