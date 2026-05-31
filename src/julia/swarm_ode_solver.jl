# Swarm ODE Solver — SDACS Phase 631
module SwarmODE
using LinearAlgebra

function rk4_step(f, t, y, h)
    k1 = f(t, y)
    k2 = f(t + h/2, y + h/2 * k1)
    k3 = f(t + h/2, y + h/2 * k2)
    k4 = f(t + h, y + h * k3)
    return y + h/6 * (k1 + 2k2 + 2k3 + k4)
end

export rk4_step
end
