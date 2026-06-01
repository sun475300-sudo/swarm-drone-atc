# Phase 631 — Julia ODE Solver for Swarm Dynamics
# Runge-Kutta 4th order solver for swarm trajectory ODEs

module SwarmODESolver

"""
    rk4_step(f, t, y, dt)

Single RK4 step for ODE y' = f(t, y).
"""
function rk4_step(f, t, y, dt)
    k1 = f(t, y)
    k2 = f(t + dt/2, y + dt/2 * k1)
    k3 = f(t + dt/2, y + dt/2 * k2)
    k4 = f(t + dt, y + dt * k3)
    return y + dt/6 * (k1 + 2k2 + 2k3 + k4)
end

"""
    solve(f, y0, t_span, dt)

Integrate ODE from t_span[1] to t_span[2] with step dt.
"""
function solve(f, y0, t_span, dt=0.01)
    t = t_span[1]
    y = y0
    trajectory = [(t, y)]
    while t < t_span[2]
        y = rk4_step(f, t, y, dt)
        t += dt
        push!(trajectory, (t, y))
    end
    return trajectory
end

end  # module SwarmODESolver
