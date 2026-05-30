% Phase 620: signal_processor — Octave/MATLAB 기반 신호 처리 모듈
% SDACS Signal Processing for Drone Telemetry

% FIR 저역통과 필터 설계
function [h, w] = design_lowpass_fir(cutoff_hz, fs, order)
    % Hanning 윈도우 기반 FIR 필터 설계
    % cutoff_hz: 차단 주파수 (Hz)
    % fs: 샘플링 주파수 (Hz)
    % order: 필터 차수 (짝수 권장)
    Wn  = cutoff_hz / (fs / 2);  % 정규화 주파수
    n   = order + 1;
    h   = zeros(1, n);
    mid = floor(n / 2);
    for i = 1:n
        if i - 1 == mid
            h(i) = 2 * Wn;
        else
            h(i) = sin(2 * pi * Wn * (i - 1 - mid)) / (pi * (i - 1 - mid));
        end
        % Hanning 윈도우 적용
        h(i) = h(i) * 0.5 * (1 - cos(2 * pi * (i - 1) / (n - 1)));
    end
    w = (0:(n-1)) / fs;
end

% FIR 필터 적용
function y = apply_fir_filter(h, x)
    n  = length(h);
    nx = length(x);
    y  = zeros(1, nx);
    for i = 1:nx
        for j = 1:min(n, i)
            y(i) = y(i) + h(j) * x(i - j + 1);
        end
    end
end

% 이동 평균 필터 (배터리 노이즈 제거)
function y = moving_average(x, window)
    n = length(x);
    y = zeros(1, n);
    for i = 1:n
        start_idx = max(1, i - floor(window / 2));
        end_idx   = min(n, i + floor(window / 2));
        y(i) = mean(x(start_idx:end_idx));
    end
end

% 드론 위치 칼만 필터 (1D 단순화)
function [pos_est, vel_est] = kalman_1d(measurements, dt, Q, R)
    % Q: 프로세스 노이즈 / R: 측정 노이즈
    n      = length(measurements);
    pos_est = zeros(1, n);
    vel_est = zeros(1, n);
    % 초기 상태
    x   = [measurements(1); 0];  % [위치; 속도]
    P   = eye(2) * 1.0;
    A   = [1, dt; 0, 1];          % 상태 전이 행렬
    H   = [1, 0];                  % 관측 행렬
    Qm  = Q * [dt^4/4, dt^3/2; dt^3/2, dt^2];
    Rm  = R;
    for i = 1:n
        % 예측 단계
        x = A * x;
        P = A * P * A' + Qm;
        % 업데이트 단계
        K   = P * H' / (H * P * H' + Rm);
        x   = x + K * (measurements(i) - H * x);
        P   = (eye(2) - K * H) * P;
        pos_est(i) = x(1);
        vel_est(i) = x(2);
    end
end

% 주파수 도메인 분석 (FFT)
function [freqs, magnitudes] = analyze_frequency(signal, fs)
    n          = length(signal);
    fft_result = fft(signal);
    magnitudes = abs(fft_result(1:floor(n/2) + 1)) / n * 2;
    freqs      = (0:floor(n/2)) * fs / n;
end

% 드론 진동 감지
function anomaly = detect_vibration_anomaly(signal, fs, threshold)
    [freqs, mags] = analyze_frequency(signal, fs);
    % 고주파 성분 에너지 비율
    low_freq_mask  = freqs < 5.0;   % 5Hz 이하: 정상 비행
    high_freq_mask = freqs >= 5.0;  % 5Hz 이상: 진동/이상
    low_energy  = sum(mags(low_freq_mask).^2);
    high_energy = sum(mags(high_freq_mask).^2);
    ratio = high_energy / (low_energy + 1e-6);
    anomaly = ratio > threshold;
    fprintf('진동 에너지 비율: %.3f (임계값: %.3f) → %s\n',
        ratio, threshold, if_else(anomaly, '이상 감지', '정상'));
end

function r = if_else(cond, a, b)
    if cond; r = a; else r = b; end
end

% 메인 실행
fprintf('SDACS Signal Processor — Phase 620\n\n');
fs  = 100;     % 샘플링 주파수 100Hz
N   = 200;     % 샘플 수
t   = (0:N-1) / fs;

% 시뮬레이션 배터리 신호 (노이즈 포함)
bat_clean = 100 - t * 20;           % 직선 감소
bat_noisy = bat_clean + randn(1, N) * 2.5;

% 이동 평균 필터 적용
bat_filtered = moving_average(bat_noisy, 10);
fprintf('배터리 필터 적용: 노이즈 제거 완료\n');
fprintf('  원본 분산: %.3f → 필터 후: %.3f\n',
    var(bat_noisy - bat_clean), var(bat_filtered - bat_clean));

% 칼만 필터 고도 추적
alt_noisy = 50 + sin(t * 2) * 2 + randn(1, N) * 1.5;
[alt_est, vel_est] = kalman_1d(alt_noisy, 1/fs, 0.1, 2.0);
fprintf('\n칼만 필터 고도 추적:\n');
fprintf('  고도 RMSE: %.3fm\n', sqrt(mean((alt_est - (50 + sin(t * 2) * 2)).^2)));

% FIR 필터 설계 및 적용
[h, ~] = design_lowpass_fir(5.0, fs, 20);
fprintf('\nFIR 저역통과 필터 (5Hz 차단): %d 탭\n', length(h));
fprintf('신호 처리 완료.\n');
