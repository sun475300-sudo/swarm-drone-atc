% Phase 558 — PID Control System Model for Drone Attitude Control
% Octave/MATLAB script implementing PID controller simulation for swarm drones.

% ===== PID Controller Parameters =====

% Proportional gain (Kp)
Kp = 2.5;

% Integral gain (Ki)
Ki = 0.8;

% Derivative gain (Kd)
Kd = 0.3;

% ===== Simulation Setup =====

dt = 0.01;          % time step (seconds)
T_total = 10.0;     % total simulation time
N = round(T_total / dt);

% Time vector
t = (0:N-1) * dt;

% Setpoint trajectory: step change at t=0, then ramp
setpoint = zeros(1, N);
setpoint(:) = 1.0;           % target altitude/angle = 1.0 unit
setpoint(round(N/2):end) = 1.5;  % step increase at mid-simulation

% ===== PID State Variables =====

output = zeros(1, N);
error = zeros(1, N);
integral_term = zeros(1, N);
derivative_term = zeros(1, N);
control_signal = zeros(1, N);

% Plant model: first-order system with inertia (simplified drone dynamics)
% y[k+1] = y[k] + dt * (u[k] - 0.5 * y[k])
plant_state = 0.0;
prev_error = 0.0;
integral_acc = 0.0;

% Anti-windup clamp for integral term
INTEGRAL_CLAMP = 5.0;
OUTPUT_CLAMP   = 10.0;

% ===== PID Simulation Loop =====

fprintf('Phase 558: PID Control System Simulation\n');
fprintf('Kp=%.2f  Ki=%.2f  Kd=%.2f  dt=%.3f  T=%.1fs\n', Kp, Ki, Kd, dt, T_total);

for k = 1:N
  % Error computation
  err = setpoint(k) - plant_state;
  error(k) = err;

  % Integral accumulation with anti-windup
  integral_acc = integral_acc + err * dt;
  integral_acc = max(-INTEGRAL_CLAMP, min(INTEGRAL_CLAMP, integral_acc));
  integral_term(k) = integral_acc;

  % Derivative term (backward difference)
  deriv = (err - prev_error) / dt;
  derivative_term(k) = deriv;

  % PID control law: u = Kp*e + Ki*∫e dt + Kd*de/dt
  u = Kp * err + Ki * integral_acc + Kd * deriv;

  % Output clamping
  u = max(-OUTPUT_CLAMP, min(OUTPUT_CLAMP, u));
  control_signal(k) = u;

  % Plant update (Euler integration of first-order system)
  plant_state = plant_state + dt * (u - 0.5 * plant_state);
  output(k) = plant_state;

  % Update previous error
  prev_error = err;
end

% ===== Performance Metrics =====

% Steady-state error (last 10% of simulation)
ss_idx = round(0.9 * N);
ss_error = mean(abs(error(ss_idx:end)));

% Overshoot: max deviation above setpoint in first 50%
first_half = output(1:round(N/2));
sp_first = setpoint(1:round(N/2));
overshoot = max(max(first_half - sp_first), 0);

% Rise time: time to reach 90% of setpoint
threshold_90 = 0.9 * setpoint(1);
rise_idx = find(output >= threshold_90, 1);
if isempty(rise_idx)
  rise_time = NaN;
else
  rise_time = t(rise_idx);
end

% ===== Report =====

fprintf('\n=== PID Performance Report ===\n');
fprintf('Steady-state error: %.4f\n', ss_error);
fprintf('Overshoot: %.4f\n', overshoot);
fprintf('Rise time: %.3f s\n', rise_time);
fprintf('Peak control: %.3f\n', max(abs(control_signal)));
fprintf('Final output: %.4f (target: %.4f)\n', output(end), setpoint(end));

% ===== Multi-Drone PID Array =====
% Simulate independent PID controllers for N_DRONES drones

N_DRONES = 6;
drone_errors = zeros(N_DRONES, 1);
drone_gains = [Kp, Ki, Kd; ...
               2.0, 1.0, 0.4; ...
               3.0, 0.5, 0.2; ...
               2.5, 0.8, 0.3; ...
               1.8, 1.2, 0.5; ...
               2.2, 0.9, 0.35];

fprintf('\n=== Multi-Drone PID Array ===\n');
for d = 1:N_DRONES
  kp_d = drone_gains(d, 1);
  ki_d = drone_gains(d, 2);
  kd_d = drone_gains(d, 3);
  % Compute steady-state gain for first-order system with PID
  % (simplified: higher Kp = lower SS error)
  ss_gain = kp_d / (0.5 + kp_d);
  drone_errors(d) = 1 - ss_gain;
  fprintf('Drone %d: Kp=%.2f Ki=%.2f Kd=%.2f  est_SS_err=%.4f\n', ...
          d, kp_d, ki_d, kd_d, drone_errors(d));
end

fprintf('\nMean SS error across drones: %.4f\n', mean(drone_errors));
fprintf('PID simulation complete.\n');
