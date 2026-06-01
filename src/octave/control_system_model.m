% Phase 558: Control System Model — 드론 PID 제어 시스템 모델 (Octave/MATLAB)
% PID altitude controller design and simulation for swarm drones.

function control_system_model()
  fprintf('Phase 558: Control System Model — 드론 PID 제어 모델\n');

  %% PID Controller parameters
  Kp = 2.5;   % Proportional gain
  Ki = 0.5;   % Integral gain
  Kd = 1.2;   % Derivative gain

  %% Simulation parameters
  dt      = 0.01;    % time step (s)
  T       = 10.0;    % total time (s)
  t       = 0:dt:T;
  n       = length(t);

  %% Drone plant model: simple double integrator (altitude)
  % z'' = u/m - g  (m = 1 kg, g = 9.81 m/s^2)
  g       = 9.81;
  m       = 1.0;
  z_ref   = 50.0;   % desired altitude (m)

  %% State vectors
  z       = zeros(1, n);  % altitude
  zdot    = zeros(1, n);  % vertical velocity
  z(1)    = 30.0;         % initial altitude
  e_int   = 0.0;
  e_prev  = z_ref - z(1);

  %% PID simulation loop
  for i = 1:n-1
    e       = z_ref - z(i);
    e_int   = e_int + e * dt;
    e_dot   = (e - e_prev) / dt;
    u       = Kp * e + Ki * e_int + Kd * e_dot;
    e_prev  = e;

    % Thrust force (clamp to physical limits)
    thrust  = max(0, min(20, u + m * g));
    zdotdot = (thrust / m) - g;
    zdot(i+1) = zdot(i) + zdotdot * dt;
    z(i+1)    = z(i)    + zdot(i) * dt;
  end

  %% Performance metrics
  steady_state_error = abs(z(end) - z_ref);
  overshoot = max(z) - z_ref;
  settling_idx = find(abs(z - z_ref) < 0.02 * abs(z_ref), 1);
  if isempty(settling_idx)
    settling_time = T;
  else
    settling_time = t(settling_idx);
  end

  fprintf('Kp=%.2f Ki=%.2f Kd=%.2f\n', Kp, Ki, Kd);
  fprintf('Steady-state error:  %.4f m\n', steady_state_error);
  fprintf('Overshoot:           %.4f m\n', max(0, overshoot));
  fprintf('Settling time (2%%):  %.3f s\n', settling_time);

  %% Transfer function analysis (Octave control package if available)
  try
    pkg load control;
    num = [Kd, Kp, Ki];
    den = [m, Kd, Kp, Ki];
    sys = tf(num, den);
    fprintf('Transfer function poles: ');
    disp(pole(sys)');
  catch
    fprintf('Control toolbox not available — skipping TF analysis.\n');
  end

  fprintf('Phase 558 simulation complete.\n');
end

% Run the simulation
control_system_model();
