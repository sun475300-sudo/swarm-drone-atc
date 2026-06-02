% Phase 558: Control System Model — GNU Octave / MATLAB
% SDACS PID control system design and simulation for drone altitude/speed control

% Phase 558 marker — PID control with Kp, Ki, Kd tuning

function control_system_model()
    fprintf('Phase 558: PID Control System Model\n\n');

    % Run altitude controller demo
    fprintf('=== Altitude PID Controller ===\n');
    [t, y, u, e] = simulate_pid_altitude();
    report_performance(t, y, 60.0, 'Altitude', 'm');

    % Run speed controller demo
    fprintf('\n=== Speed PID Controller ===\n');
    [t2, y2, u2, e2] = simulate_pid_speed();
    report_performance(t2, y2, 10.0, 'Speed', 'm/s');

    % Frequency response analysis
    fprintf('\n=== Frequency Response Analysis ===\n');
    analyze_frequency_response();
end

% ============================================================
% PID controller structure

function pid = create_pid(Kp, Ki, Kd, dt, u_min, u_max)
    pid.Kp    = Kp;
    pid.Ki    = Ki;
    pid.Kd    = Kd;
    pid.dt    = dt;
    pid.u_min = u_min;
    pid.u_max = u_max;
    pid.integral   = 0;
    pid.prev_error = 0;
end

function [u, pid] = pid_update(pid, setpoint, measured)
    error      = setpoint - measured;
    pid.integral = pid.integral + error * pid.dt;

    % Anti-windup: clamp integral
    pid.integral = max(-100, min(100, pid.integral));

    derivative = (error - pid.prev_error) / pid.dt;
    pid.prev_error = error;

    u = pid.Kp * error + pid.Ki * pid.integral + pid.Kd * derivative;
    u = max(pid.u_min, min(pid.u_max, u));  % saturate output
end

% ============================================================
% Altitude control simulation (first-order drone dynamics)

function [t, y, u_hist, e_hist] = simulate_pid_altitude()
    dt       = 0.05;   % 20 Hz control loop
    T_sim    = 30.0;   % 30 seconds
    setpoint = 60.0;   % target altitude in meters

    % PID gains tuned for altitude control
    Kp = 1.5;
    Ki = 0.3;
    Kd = 0.8;
    pid = create_pid(Kp, Ki, Kd, dt, -10, 10);

    % Plant: simple first-order: dy/dt = u - drag
    tau   = 2.0;   % time constant
    y     = 0.0;   % initial altitude
    n     = round(T_sim / dt);
    t     = (0:n-1) * dt;
    y_hist = zeros(1, n);
    u_hist = zeros(1, n);
    e_hist = zeros(1, n);

    fprintf('Kp=%.2f Ki=%.2f Kd=%.2f\n', Kp, Ki, Kd);
    for i = 1:n
        [u, pid]  = pid_update(pid, setpoint, y);
        dy        = (u - y / tau) * dt;
        y         = max(0, y + dy);
        y_hist(i) = y;
        u_hist(i) = u;
        e_hist(i) = setpoint - y;
    end
    y = y_hist;
end

% ============================================================
% Speed control simulation

function [t, y, u_hist, e_hist] = simulate_pid_speed()
    dt       = 0.1;
    T_sim    = 20.0;
    setpoint = 10.0;  % m/s

    Kp = 2.0;
    Ki = 0.5;
    Kd = 0.4;
    pid = create_pid(Kp, Ki, Kd, dt, 0, 20);

    % Wind disturbance simulation
    rng_seed = 558;
    rand('state', rng_seed);
    wind = 2.0 * sin(2*pi*(0:round(T_sim/dt)-1)*dt / 5.0);

    y    = 0.0;
    n    = round(T_sim / dt);
    t    = (0:n-1) * dt;
    y_hist = zeros(1, n);
    u_hist = zeros(1, n);
    e_hist = zeros(1, n);

    fprintf('Kp=%.2f Ki=%.2f Kd=%.2f (with wind disturbance)\n', Kp, Ki, Kd);
    for i = 1:n
        [u, pid]  = pid_update(pid, setpoint, y);
        dy        = (u - y * 0.5 + wind(i)) * dt;
        y         = max(0, y + dy);
        y_hist(i) = y;
        u_hist(i) = u;
        e_hist(i) = setpoint - y;
    end
    y = y_hist;
end

% ============================================================
% Performance metrics

function report_performance(t, y, setpoint, label, unit)
    % Steady-state error (last 20% of simulation)
    ss_idx = round(0.8 * length(t)):length(t);
    ss_err = mean(abs(setpoint - y(ss_idx)));

    % Rise time (10% -> 90% of setpoint)
    idx_10 = find(y >= 0.1 * setpoint, 1);
    idx_90 = find(y >= 0.9 * setpoint, 1);
    rise_time = (idx_90 - idx_10) * (t(2) - t(1));

    % Overshoot
    max_y    = max(y);
    overshoot = max(0, (max_y - setpoint) / setpoint * 100);

    fprintf('  Rise time:       %.2f s\n', rise_time);
    fprintf('  Overshoot:       %.1f%%\n', overshoot);
    fprintf('  Steady-state err: %.3f %s\n', ss_err, unit);
    fprintf('  Final value:      %.2f %s (setpoint: %.1f)\n', y(end), unit, setpoint);
end

% ============================================================
% Frequency response (Bode-like analysis)

function analyze_frequency_response()
    freqs = logspace(-2, 2, 50);  % 0.01 to 100 rad/s
    Kp = 1.5; Ki = 0.3; Kd = 0.8;

    magnitudes = zeros(size(freqs));
    phases     = zeros(size(freqs));

    for i = 1:length(freqs)
        w = freqs(i);
        s = 1j * w;
        % PID transfer function: Kp + Ki/s + Kd*s
        C = Kp + Ki/s + Kd*s;
        % First-order plant: G = 1/(tau*s + 1), tau=2
        G = 1 / (2*s + 1);
        L = C * G;  % open-loop
        magnitudes(i) = 20 * log10(abs(L));
        phases(i)     = angle(L) * 180 / pi;
    end

    % Gain margin and phase margin (simplified)
    phase_crossover = find(diff(sign(phases + 180)) ~= 0, 1);
    gain_margin_db  = -magnitudes(phase_crossover);
    fprintf('  Gain margin:   ~%.1f dB\n', gain_margin_db);

    gain_crossover = find(diff(sign(magnitudes)) ~= 0, 1);
    phase_margin   = 180 + phases(gain_crossover);
    fprintf('  Phase margin:  ~%.1f deg\n', phase_margin);
    fprintf('  System is %s\n', ...
        (phase_margin > 0 && gain_margin_db > 0) ? 'STABLE' : 'UNSTABLE');
end

% Execute main function
control_system_model();
