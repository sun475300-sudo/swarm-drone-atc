% P558: ControlSystemModel - Octave PID control for drone altitude
% Phase 558: PID controller design and simulation for altitude hold

function result = control_system_model()
  % PID controller parameters for altitude control
  Kp = 2.0;    % Proportional gain
  Ki = 0.5;    % Integral gain
  Kd = 1.0;    % Derivative gain

  % Simulation parameters
  dt      = 0.01;   % Time step [s]
  t_end   = 30.0;   % Simulation duration [s]
  t       = 0:dt:t_end;
  n       = length(t);

  % Target altitude setpoint
  setpoint = 60.0;  % meters

  % State variables
  altitude    = zeros(1, n);
  velocity    = zeros(1, n);
  pid_output  = zeros(1, n);
  error_int   = 0.0;
  error_prev  = 0.0;

  % Initial conditions
  altitude(1) = 0.0;
  velocity(1) = 0.0;

  % Drone physics parameters
  mass       = 1.5;   % kg
  drag_coeff = 0.3;
  gravity    = 9.81;

  % PID simulation loop
  for i = 2:n
    % Compute PID error
    error      = setpoint - altitude(i-1);
    error_int  = error_int + error * dt;
    error_deriv = (error - error_prev) / dt;
    error_prev  = error;

    % PID controller output (thrust command)
    pid_ctrl    = Kp * error + Ki * error_int + Kd * error_deriv;
    pid_output(i) = pid_ctrl;

    % Clamp thrust
    thrust = max(0, min(pid_ctrl, 30.0));

    % Drone dynamics: F = ma
    accel = (thrust - mass * gravity - drag_coeff * velocity(i-1)) / mass;
    velocity(i)  = velocity(i-1) + accel * dt;
    altitude(i)  = altitude(i-1) + velocity(i) * dt;
    altitude(i)  = max(0, altitude(i));
  end

  % Compute performance metrics
  steady_state_error = abs(setpoint - altitude(end));
  settling_idx = find(abs(altitude - setpoint) < 0.05 * setpoint, 1);
  settling_time = t(settling_idx);
  overshoot = max(0, (max(altitude) - setpoint) / setpoint * 100);

  result = struct(
    'time', t,
    'altitude', altitude,
    'velocity', velocity,
    'pid_output', pid_output,
    'steady_state_error', steady_state_error,
    'settling_time', settling_time,
    'overshoot_pct', overshoot,
    'Kp', Kp,
    'Ki', Ki,
    'Kd', Kd
  );

  printf('=== PID Controller Results (P558) ===\n');
  printf('Kp=%.1f  Ki=%.2f  Kd=%.1f\n', Kp, Ki, Kd);
  printf('Settling time: %.2f s\n', settling_time);
  printf('Overshoot: %.1f%%\n', overshoot);
  printf('Steady-state error: %.4f m\n', steady_state_error);
end
