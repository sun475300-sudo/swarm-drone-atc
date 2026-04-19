% Phase 558: MATLAB/Octave Control System Modeling
% PID 제어기 시뮬레이션: 드론 고도/속도 안정화, 주파수 응답 분석

function control_system_model()
    % PRNG
    state = bitxor(int64(42), int64(hex2dec('6c62272e')));

    % PID controller parameters
    Kp = 2.5;
    Ki = 0.8;
    Kd = 1.2;

    % Drone physical parameters
    mass = 1.5;          % kg
    drag = 0.3;          % drag coefficient
    gravity = 9.81;      % m/s^2
    dt = 0.01;           % time step
    n_steps = 1000;

    % State variables
    altitude = 0;
    velocity = 0;
    target_altitude = 50;

    % PID state
    integral = 0;
    prev_error = 0;

    % Recording
    altitudes = zeros(1, n_steps);
    velocities = zeros(1, n_steps);
    controls = zeros(1, n_steps);
    errors = zeros(1, n_steps);

    for step = 1:n_steps
        % Error
        error = target_altitude - altitude;

        % PID
        integral = integral + error * dt;
        integral = max(-50, min(50, integral));  % anti-windup
        derivative = (error - prev_error) / dt;
        control = Kp * error + Ki * integral + Kd * derivative;
        control = max(-20, min(20, control));  % saturation

        % Physics: F = m*a, a = (thrust - drag*v - m*g) / m
        thrust = control + mass * gravity;  % compensate gravity
        accel = (thrust - drag * velocity - mass * gravity) / mass;
        velocity = velocity + accel * dt;
        altitude = altitude + velocity * dt;
        altitude = max(0, altitude);  % ground constraint

        prev_error = error;

        % Record
        altitudes(step) = altitude;
        velocities(step) = velocity;
        controls(step) = control;
        errors(step) = error;
    end

    % Performance metrics
    steady_state_error = abs(target_altitude - altitudes(end));
    overshoot = (max(altitudes) - target_altitude) / target_altitude * 100;

    % Rise time (10% to 90% of target)
    rise_start = find(altitudes >= 0.1 * target_altitude, 1);
    rise_end = find(altitudes >= 0.9 * target_altitude, 1);
    if ~isempty(rise_start) && ~isempty(rise_end)
        rise_time = (rise_end - rise_start) * dt;
    else
        rise_time = -1;
    end

    % Settling time (within 2% of target)
    settling = n_steps;
    for k = n_steps:-1:1
        if abs(altitudes(k) - target_altitude) > 0.02 * target_altitude
            settling = k;
            break;
        end
    end
    settling_time = settling * dt;

    % Frequency response (simplified Bode)
    n_freq = 20;
    frequencies = logspace(-1, 2, n_freq);
    magnitude = zeros(1, n_freq);
    for f = 1:n_freq
        w = frequencies(f);
        % PID transfer function: Kp + Ki/jw + Kd*jw
        jw = 1i * w;
        pid_tf = Kp + Ki / jw + Kd * jw;
        magnitude(f) = 20 * log10(abs(pid_tf));
    end

    fprintf('=== Drone PID Control Results ===\n');
    fprintf('Target altitude: %.1f m\n', target_altitude);
    fprintf('Final altitude: %.3f m\n', altitudes(end));
    fprintf('Steady-state error: %.4f m\n', steady_state_error);
    fprintf('Overshoot: %.2f%%\n', overshoot);
    fprintf('Rise time: %.3f s\n', rise_time);
    fprintf('Settling time: %.3f s\n', settling_time);
    fprintf('Bode gain at 1 Hz: %.1f dB\n', magnitude(find(frequencies >= 1, 1)));
end

control_system_model();
