# Phase 631 — Swarm ODE Solver (RK4) in Julia
using DifferentialEquations

struct DroneState
    pos::Vector{Float64}
    vel::Vector{Float64}
end

function swarm_ode!(du, u, p, t)
    n = length(u) ÷ 6
    for i in 1:n
        idx = (i-1)*6
        du[idx+1:idx+3] = u[idx+4:idx+6]
        du[idx+4:idx+6] = p.force(u, i, t)
    end
end

function solve_swarm(initial_states, tspan; dt=0.01)
    u0 = vcat([vcat(s.pos, s.vel) for s in initial_states]...)
    prob = ODEProblem(swarm_ode!, u0, tspan)
    solve(prob, RK4(), dt=dt)
end
