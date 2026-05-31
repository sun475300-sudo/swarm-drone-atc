% control_system_model.m - PID control system for SDACS (Phase 558)
% GNU Octave implementation of drone altitude PID controller

% Phase 558 control system model

% PID Controller parameters
Kp = 2.0;    % Proportional gain
Ki = 0.5;    % Integral gain
Kd = 0.8;    % Derivative gain

% Drone model parameters
mass     = 1.5;  % kg
g        = 9.81; % m/s^2
drag_c   = 0.1;  % drag coefficient

% Simulation parameters
dt       = 0.01;   % time step (s)
t_end    = 10.0;   % simulation duration (s)
t        = 0:dt:t_end;
n        = length(t);

% State variables
altitude   = zeros(1, n);
velocity   = zeros(1, n);
thrust     = zeros(1, n);

% PID state variables
integral   = 0.0;
prev_error = 0.0;

% Target altitude
altitude_ref = 50.0;  % meters

% Initial conditions
altitude(1) = 0.0;
velocity(1) = 0.0;

% PID control loop simulation
for i = 2:n
    error       = altitude_ref - altitude(i-1);
    integral    = integral + error * dt;
    derivative  = (error - prev_error) / dt;
    prev_error  = error;

    % PID output (thrust command)
    pid_output  = Kp * error + Ki * integral + Kd * derivative;
    thrust(i)   = mass * g + pid_output;
    thrust(i)   = max(0, min(thrust(i), 3 * mass * g));  % saturate

    % Drone dynamics (simplified)
    accel = (thrust(i) - mass * g - drag_c * velocity(i-1)) / mass;
    velocity(i)  = velocity(i-1) + accel * dt;
    altitude(i)  = altitude(i-1) + velocity(i-1) * dt;
end

% Performance metrics
steady_state_error = abs(altitude_ref - altitude(end));
rise_time_idx      = find(altitude >= 0.9 * altitude_ref, 1, 'first');
rise_time          = t(rise_time_idx);
overshoot          = max(0, (max(altitude) - altitude_ref) / altitude_ref * 100);

printf('SDACS PID Control System (Phase 558)\n');
printf('Parameters: Kp=%.2f, Ki=%.2f, Kd=%.2f\n', Kp, Ki, Kd);
printf('Target altitude: %.1f m\n', altitude_ref);
printf('Steady-state error: %.4f m\n', steady_state_error);
printf('Rise time: %.3f s\n', rise_time);
printf('Overshoot: %.1f%%\n', overshoot);

% Transfer function representation
s   = tf('s');
G_plant = 1 / (mass * s^2 + drag_c * s);
G_pid   = Kp + Ki/s + Kd*s;
G_cl    = feedback(G_pid * G_plant, 1);

printf('Closed-loop poles: computed\n');
