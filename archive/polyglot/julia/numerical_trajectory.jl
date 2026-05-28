# Phase 554: Julia Numerical Trajectory Optimization
# 수치 최적화 궤적: 그래디언트 디센트 + 제약 최적화로 에너지 최소 경로 계산

mutable struct PRNG554
    state::UInt64
end

function PRNG554(seed::UInt64)
    PRNG554(seed ⊻ 0x6c62272e07bb0142)
end

function next!(rng::PRNG554)::UInt64
    rng.state ⊻= rng.state << 13
    rng.state ⊻= rng.state >> 7
    rng.state ⊻= rng.state << 17
    return rng.state
end

function uniform554(rng::PRNG554)::Float64
    Float64(next!(rng) & 0x7FFFFFFF) / Float64(0x7FFFFFFF)
end

function normal554(rng::PRNG554)::Float64
    u1 = max(uniform554(rng), 1e-10)
    u2 = uniform554(rng)
    sqrt(-2.0 * log(u1)) * cos(2π * u2)
end

struct WP554
    x::Float64
    y::Float64
    z::Float64
end

function dist554(a::WP554, b::WP554)::Float64
    sqrt((a.x - b.x)^2 + (a.y - b.y)^2 + (a.z - b.z)^2)
end

function path_energy554(wps::Vector{WP554})::Float64
    e = 0.0
    for i in 1:length(wps)-1
        d = dist554(wps[i], wps[i+1])
        dz = wps[i+1].z - wps[i].z
        e += d + max(0.0, dz) * 2.0
    end
    e
end

function smoothness554(wps::Vector{WP554})::Float64
    length(wps) < 3 && return 0.0
    total = 0.0
    for i in 2:length(wps)-1
        dx1 = wps[i].x - wps[i-1].x
        dy1 = wps[i].y - wps[i-1].y
        dx2 = wps[i+1].x - wps[i].x
        dy2 = wps[i+1].y - wps[i].y
        turn = abs(atan(dy2, dx2) - atan(dy1, dx1))
        total += turn
    end
    total
end

function optimize_traj(start::WP554, goal::WP554, n_wp::Int, rng::PRNG554;
                       iters::Int=200, lr::Float64=0.5)
    wps = WP554[start]
    for i in 1:n_wp
        t = Float64(i) / Float64(n_wp + 1)
        push!(wps, WP554(
            start.x + t*(goal.x-start.x) + normal554(rng)*5,
            start.y + t*(goal.y-start.y) + normal554(rng)*5,
            start.z + t*(goal.z-start.z) + normal554(rng)*2
        ))
    end
    push!(wps, goal)

    best_e = path_energy554(wps)
    best_wps = copy(wps)

    for _ in 1:iters
        idx = 2 + Int(floor(uniform554(rng) * n_wp))
        idx > length(wps)-1 && (idx = length(wps)-1)
        old = wps[idx]
        wps[idx] = WP554(
            old.x + normal554(rng)*lr,
            old.y + normal554(rng)*lr,
            max(5.0, old.z + normal554(rng)*lr*0.5)
        )
        new_e = path_energy554(wps) + 0.5*smoothness554(wps)
        if new_e < best_e
            best_e = new_e
            best_wps = copy(wps)
        else
            wps[idx] = old
        end
    end
    best_wps, best_e
end

function main554()
    rng = PRNG554(UInt64(42))
    s = WP554(0.0, 0.0, 50.0)
    g = WP554(200.0, 150.0, 50.0)
    best = Inf
    for i in 1:5
        wps, e = optimize_traj(s, g, 8, rng, iters=100)
        e < best && (best = e)
        println("Trajectory $i: energy=$(round(e, digits=2)), waypoints=$(length(wps))")
    end
    println("Best energy: $(round(best, digits=2))")
end

main554()
