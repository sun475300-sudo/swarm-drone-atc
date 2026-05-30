% Phase 558: control_system_model — Octave/MATLAB 기반 제어 시스템 모델
% SDACS Control System Model and PID Tuning

% PID 컨트롤러 파라미터 구조체
function ctrl = create_pid_controller(Kp, Ki, Kd, dt, anti_windup)
    % PID controller 생성
    % Kp: 비례 이득 / Ki: 적분 이득 / Kd: 미분 이득
    ctrl.Kp = Kp;
    ctrl.Ki = Ki;
    ctrl.Kd = Kd;
    ctrl.dt = dt;
    ctrl.anti_windup = anti_windup;
    ctrl.integral = 0;
    ctrl.prev_error = 0;
    ctrl.output_min = -1.0;
    ctrl.output_max = 1.0;
end

% PID 업데이트 (1 스텝)
function [output, ctrl] = pid_update(ctrl, setpoint, measurement)
    error = setpoint - measurement;
    % 비례항
    P = ctrl.Kp * error;
    % 적분항 (Anti-windup 클램핑)
    ctrl.integral = ctrl.integral + error * ctrl.dt;
    if ctrl.anti_windup
        ctrl.integral = max(ctrl.output_min / ctrl.Ki, ...
                            min(ctrl.output_max / ctrl.Ki, ctrl.integral));
    end
    I = ctrl.Ki * ctrl.integral;
    % 미분항
    D = ctrl.Kd * (error - ctrl.prev_error) / ctrl.dt;
    ctrl.prev_error = error;
    % 출력 클램핑
    raw = P + I + D;
    output = max(ctrl.output_min, min(ctrl.output_max, raw));
end

% 드론 고도 제어 시뮬레이션
function [alt_history, ctrl_history] = simulate_altitude_control(target_alt, dt, n_steps)
    % 초기 상태
    alt = 0.0;
    vel = 0.0;
    g   = 9.81;
    mass = 1.5;  % kg
    drag = 0.3;

    % PID 파라미터 설정 (Kp=2.0, Ki=0.5, Kd=1.0)
    Kp = 2.0;
    Ki = 0.5;
    Kd = 1.0;
    ctrl = create_pid_controller(Kp, Ki, Kd, dt, true);

    alt_history  = zeros(1, n_steps);
    ctrl_history = zeros(1, n_steps);

    for i = 1:n_steps
        [thrust_norm, ctrl] = pid_update(ctrl, target_alt, alt);
        thrust = (g * mass) * (1 + thrust_norm);  % 중력 보상 + 제어 출력
        accel = (thrust - mass * g - drag * vel) / mass;
        vel = vel + accel * dt;
        alt = max(0, alt + vel * dt);
        alt_history(i)  = alt;
        ctrl_history(i) = thrust_norm;
    end
end

% 스웜 위치 제어 시뮬레이션 (편대 유지)
function formation_error = simulate_swarm_formation(n_drones, dt, n_steps)
    formation_error = zeros(n_steps, 1);
    % 목표 편대: 드론 0을 중심으로 반경 10m 원형 배치
    radius = 10.0;
    targets = zeros(n_drones, 2);
    for d = 1:n_drones
        angle = (d - 1) * 2 * pi / n_drones;
        targets(d, :) = [radius * cos(angle), radius * sin(angle)];
    end

    % 각 드론에 PID controller (x, y 독립)
    ctrls_x = cell(n_drones, 1);
    ctrls_y = cell(n_drones, 1);
    for d = 1:n_drones
        ctrls_x{d} = create_pid_controller(1.5, 0.2, 0.8, dt, true);
        ctrls_y{d} = create_pid_controller(1.5, 0.2, 0.8, dt, true);
    end

    positions = zeros(n_drones, 2);  % 초기 위치 (원점)

    for step = 1:n_steps
        err_sum = 0;
        for d = 1:n_drones
            [vx, ctrls_x{d}] = pid_update(ctrls_x{d}, targets(d,1), positions(d,1));
            [vy, ctrls_y{d}] = pid_update(ctrls_y{d}, targets(d,2), positions(d,2));
            positions(d, :) = positions(d, :) + [vx, vy] * dt;
            err_sum = err_sum + norm(positions(d,:) - targets(d,:));
        end
        formation_error(step) = err_sum / n_drones;
    end
end

% 메인 실행
fprintf('SDACS Control System Model — Phase 558\n\n');
dt     = 0.05;  % 50ms 제어 루프
n_steps = 200;

% 고도 제어 시뮬레이션
target = 50.0;  % 50m
[alt_hist, ctrl_hist] = simulate_altitude_control(target, dt, n_steps);
fprintf('고도 제어 시뮬레이션:\n');
fprintf('  목표 고도: %.1fm\n', target);
fprintf('  최종 고도: %.2fm\n', alt_hist(end));
fprintf('  정착 오차: %.4fm\n', abs(alt_hist(end) - target));

% 편대 제어 시뮬레이션
fprintf('\n편대 제어 시뮬레이션:\n');
form_err = simulate_swarm_formation(5, dt, n_steps);
fprintf('  초기 오차: %.2fm\n', form_err(1));
fprintf('  최종 오차: %.2fm\n', form_err(end));
fprintf('  오차 감소율: %.1f%%\n', 100 * (form_err(1) - form_err(end)) / form_err(1));
fprintf('\nPID 파라미터: Kp=%.1f Ki=%.1f Kd=%.1f\n', 2.0, 0.5, 1.0);
