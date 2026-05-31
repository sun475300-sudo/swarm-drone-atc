# Phase 631 — Swarm ODE Solver (Julia)
# DifferentialEquations.jl 기반 군집 드론 ODE 적분기

module SwarmODESolver

using LinearAlgebra

"""
    DroneState

드론의 3D 위치/속도 상태.
"""
struct DroneState
    pos::Vector{Float64}  # [x, y, z] in metres
    vel::Vector{Float64}  # [vx, vy, vz] in m/s
end

"""
    swarm_ode!(du, u, p, t)

군집 드론 동역학 ODE (APF 기반).
u = [x1,y1,z1,vx1,vy1,vz1, ..., xN,yN,zN,vxN,vyN,vzN]
"""
function swarm_ode!(du, u, p, t)
    n_drones = p[:n_drones]
    k_attr   = get(p, :k_attr, 1.0)
    k_rep    = get(p, :k_rep, 500.0)
    d_safe   = get(p, :d_safe, 20.0)

    for i in 1:n_drones
        base = (i - 1) * 6
        pos_i = u[base+1:base+3]
        vel_i = u[base+4:base+6]

        # 목표 지점 인력
        goal = get(p, :goals, [zeros(3) for _ in 1:n_drones])[i]
        f_attr = k_attr .* (goal .- pos_i)

        # 인접 드론 간 척력
        f_rep = zeros(3)
        for j in 1:n_drones
            j == i && continue
            base_j = (j - 1) * 6
            pos_j  = u[base_j+1:base_j+3]
            diff   = pos_i .- pos_j
            dist   = norm(diff)
            if dist < d_safe && dist > 1e-6
                f_rep .+= k_rep .* diff ./ dist^3
            end
        end

        du[base+1:base+3] .= vel_i
        du[base+4:base+6] .= f_attr .+ f_rep
    end
end

end  # module
