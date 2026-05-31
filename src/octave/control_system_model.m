% control_system_model.m
% Phase 558 — Octave PID Control System Model for swarm drone ATC.
% Simulates PID altitude and velocity controllers with Kp, Ki, Kd gain tuning.

% ── PID parameters ──────────────────────────────────────────────────────────

% Altitude PID gains (Phase 558)
Kp_alt = 2.0;   % Proportional gain Kp
Ki_alt = 0.4;   % Integral gain     Ki
Kd_alt = 0.8;   % Derivative gain   Kd

% Velocity PID gains
Kp_vel = 1.5;   % Proportional gain Kp (velocity loop)
Ki_vel = 0.2;   % Integral gain     Ki (velocity loop)
Kd_vel = 0.3;   % Derivative gain   Kd (velocity loop)

% ── Simulation parameters ────────────────────────────────────────────────────

dt        = 0.01;           % time step (s)
t_end     = 20.0;           % simulation duration (s)
t         = 0:dt:t_end;
N         = length(t);

% Reference setpoints
alt_ref   = 50.0;           % target altitude (m)
vel_ref   =  5.0;           % target horizontal speed (m/s)

% ── PID state initialisation ─────────────────────────────────────────────────

% Altitude controller state
alt_err_prev  = 0.0;
alt_integral  = 0.0;
altitude      = zeros(1, N);
altitude(1)   = 0.0;        % start on ground

% Velocity controller state
vel_err_prev  = 0.0;
vel_integral  = 0.0;
velocity      = zeros(1, N);
velocity(1)   = 0.0;

% PID output histories
pid_alt_output = zeros(1, N);
pid_vel_output = zeros(1, N);

% ── Simple 1-D drone dynamics (double integrator + drag) ─────────────────────
% alt_ddot = (thrust - drag*alt_dot - g) / mass
mass  = 1.5;    % kg
g     = 9.81;   % m/s²
drag  = 0.3;    % Ns/m  (linear drag coefficient)

alt_dot   = 0.0;   % vertical velocity
vel_dot   = 0.0;   % horizontal acceleration state

% ── Main simulation loop ──────────────────────────────────────────────────────

fprintf('[558] PID Control System Model — Phase 558\n');
fprintf('[558] Kp_alt=%.2f Ki_alt=%.2f Kd_alt=%.2f\n', Kp_alt, Ki_alt, Kd_alt);
fprintf('[558] Kp_vel=%.2f Ki_vel=%.2f Kd_vel=%.2f\n', Kp_vel, Ki_vel, Kd_vel);

for k = 2:N
    % ── Altitude PID ──────────────────────────────────────────────────────────
    alt_err        = alt_ref - altitude(k-1);
    alt_integral   = alt_integral + alt_err * dt;
    alt_derivative = (alt_err - alt_err_prev) / dt;

    % Integral anti-windup clamp
    alt_integral   = max(-20.0, min(20.0, alt_integral));

    u_alt = Kp_alt * alt_err  + Ki_alt * alt_integral  + Kd_alt * alt_derivative;
    alt_err_prev  = alt_err;
    pid_alt_output(k) = u_alt;

    % Thrust force (PID output drives vertical accel)
    thrust       = mass * (u_alt + g);
    alt_ddot     = (thrust - drag * alt_dot - mass * g) / mass;
    alt_dot      = alt_dot + alt_ddot * dt;
    altitude(k)  = altitude(k-1) + alt_dot * dt;

    % ── Velocity PID ─────────────────────────────────────────────────────────
    vel_err        = vel_ref - velocity(k-1);
    vel_integral   = vel_integral + vel_err * dt;
    vel_derivative = (vel_err - vel_err_prev) / dt;
    vel_integral   = max(-10.0, min(10.0, vel_integral));

    u_vel = Kp_vel * vel_err + Ki_vel * vel_integral + Kd_vel * vel_derivative;
    vel_err_prev  = vel_err;
    pid_vel_output(k) = u_vel;

    vel_dot       = u_vel - drag * velocity(k-1);
    velocity(k)   = velocity(k-1) + vel_dot * dt;
end

% ── Results summary ───────────────────────────────────────────────────────────

final_alt  = altitude(end);
final_vel  = velocity(end);
alt_sse    = (alt_ref - final_alt)^2;
vel_sse    = (vel_ref - final_vel)^2;

fprintf('[558] Final altitude : %.4f m  (setpoint=%.1f, SSE=%.6f)\n', ...
        final_alt, alt_ref, alt_sse);
fprintf('[558] Final velocity : %.4f m/s (setpoint=%.1f, SSE=%.6f)\n', ...
        final_vel, vel_ref, vel_sse);

% Settling time estimate (within 2% of setpoint)
tol_alt = 0.02 * alt_ref;
settled_idx_alt = find(abs(altitude - alt_ref) <= tol_alt, 1);
if ~isempty(settled_idx_alt)
    fprintf('[558] Altitude settled at t=%.2f s\n', t(settled_idx_alt));
else
    fprintf('[558] Altitude did not settle within simulation window\n');
end

% ── Optional plots (only when running interactively) ─────────────────────────

if exist('OCTAVE_VERSION', 'builtin') && ~isempty(getenv('DISPLAY'))
    figure(1);
    subplot(2, 1, 1);
    plot(t, altitude, 'b-', t, repmat(alt_ref, 1, N), 'r--');
    xlabel('Time (s)'); ylabel('Altitude (m)');
    title('[558] Altitude PID Response (Kp=2.0, Ki=0.4, Kd=0.8)');
    legend('altitude', 'setpoint');
    grid on;

    subplot(2, 1, 2);
    plot(t, velocity, 'g-', t, repmat(vel_ref, 1, N), 'r--');
    xlabel('Time (s)'); ylabel('Speed (m/s)');
    title('[558] Velocity PID Response');
    legend('velocity', 'setpoint');
    grid on;
end

% ── Gain sweep utility function ───────────────────────────────────────────────

function [alt_final, sse] = simulate_altitude_pid(Kp, Ki, Kd, alt_ref_val)
    % Compact PID simulation used for parameter sweep / gain tuning.
    % Returns final altitude and steady-state error for given PID gains.
    dt_s    = 0.01;
    steps   = 2000;
    alt     = 0.0;
    alt_dot = 0.0;
    err_p   = 0.0;
    intg    = 0.0;
    mass_v  = 1.5;
    drag_v  = 0.3;
    g_v     = 9.81;

    for i = 1:steps
        err   = alt_ref_val - alt;
        intg  = max(-20, min(20, intg + err * dt_s));
        deriv = (err - err_p) / dt_s;
        u     = Kp * err + Ki * intg + Kd * deriv;
        err_p = err;
        thrust  = mass_v * (u + g_v);
        acc     = (thrust - drag_v * alt_dot - mass_v * g_v) / mass_v;
        alt_dot = alt_dot + acc * dt_s;
        alt     = alt + alt_dot * dt_s;
    end
    alt_final = alt;
    sse       = (alt_ref_val - alt)^2;
end

% Demo gain sweep
fprintf('\n[558] Gain sweep: varying Kp\n');
for kp_test = [0.5, 1.0, 2.0, 3.0, 4.0]
    [af, se] = simulate_altitude_pid(kp_test, 0.4, 0.8, 50.0);
    fprintf('  Kp=%.1f -> alt_final=%.4f m  SSE=%.6f\n', kp_test, af, se);
end
