# swarm_ode_solver.jl - ODE solver for drone swarm dynamics
module SwarmODESolver

using LinearAlgebra

struct DroneParams
    mass::Float64
    drag::Float64
    k_att::Float64
    k_rep::Float64
    rep_radius::Float64
end

function apf_force(pos_i, positions, params::DroneParams)
    force = zeros(3)
    for pos_j in positions
        diff = pos_i .- pos_j
        dist = norm(diff)
        if 0.01 < dist < params.rep_radius
            mag = params.k_rep * (1/dist - 1/params.rep_radius) / dist^2
            force .+= mag .* diff ./ dist
        end
    end
    return force
end

function swarm_ode!(du, u, params, t)
    n = length(params)
    positions = [u[(6i-5):(6i-3)] for i in 1:n]
    for i in 1:n
        p = (6i-5):(6i)
        pos = u[p[1:3]]
        vel = u[p[4:6]]
        force = apf_force(pos, positions, params[i])
        du[p[1:3]] .= vel
        du[p[4:6]] .= (force .- params[i].drag .* vel) ./ params[i].mass
    end
end

export DroneParams, apf_force, swarm_ode!
end
