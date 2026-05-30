% SDACS Signal Processor — Octave/MATLAB (Phase 620)
% 드론 군집 신호 처리 (FFT, 필터링, 스펙트럼 분석)

function result = compute_fft(signal, fs)
    % FFT 계산 및 주파수 스펙트럼 반환
    n = length(signal);
    fft_result = fft(signal);
    magnitude = abs(fft_result(1:floor(n/2)+1));
    freqs = (0:floor(n/2)) * fs / n;
    result = struct('freqs', freqs, 'magnitude', magnitude, 'n', n);
end

function filtered = lowpass_filter(signal, cutoff, fs, order)
    % 단순 이동 평균 저주파 통과 필터 (Phase 620)
    if nargin < 4
        order = max(1, floor(fs / (cutoff * 2)));
    end
    b = ones(1, order) / order;
    filtered = conv(signal, b, 'same');
end

function filtered = highpass_filter(signal, cutoff, fs)
    % 단순 고주파 통과 필터 (원래 - 저주파)
    lp = lowpass_filter(signal, cutoff, fs);
    filtered = signal - lp;
end

function [freqs, psd] = power_spectral_density(signal, fs)
    % Welch 방식 PSD 근사 (단순화)
    n = length(signal);
    windowed = signal .* hanning(n)';
    fft_result = fft(windowed);
    psd = abs(fft_result(1:floor(n/2)+1)).^2 / (fs * n);
    psd(2:end-1) = 2 * psd(2:end-1);  % 단측 스펙트럼
    freqs = (0:floor(n/2)) * fs / n;
end

function peaks = find_spectral_peaks(freqs, magnitude, n_peaks)
    % 스펙트럼 피크 탐지
    if nargin < 3
        n_peaks = 5;
    end
    [sorted_mag, idx] = sort(magnitude, 'descend');
    peaks = struct();
    peaks.frequencies = freqs(idx(1:min(n_peaks, length(idx))));
    peaks.magnitudes  = sorted_mag(1:min(n_peaks, length(idx)));
end

function vibration = analyze_drone_vibration(telemetry_z, fs)
    % 드론 수직 가속도 진동 분석
    detrended = telemetry_z - mean(telemetry_z);
    spec = compute_fft(detrended, fs);
    [~, max_idx] = max(spec.magnitude);
    dominant_freq = spec.freqs(max_idx);
    rms = sqrt(mean(detrended.^2));
    
    vibration = struct(
        'rms', rms,
        'dominant_freq', dominant_freq,
        'is_excessive', rms > 2.0,
        'spectrum', spec
    );
end

function demo_signal_processing()
    % 데모: 드론 고도 신호 처리 (Phase 620)
    fs = 100;  % 100 Hz 샘플링
    t = 0:1/fs:9.99;
    
    % 복합 신호 (기본 비행 + 진동 + 노이즈)
    altitude = 100 + 5*sin(2*pi*0.5*t) + 0.5*sin(2*pi*10*t) + 0.2*randn(size(t));
    
    fprintf('=== Signal Processor (Phase 620) ===\n');
    fprintf('Signal length: %d samples @ %d Hz\n', length(altitude), fs);
    
    % 저주파 통과 필터로 진동 제거
    smoothed = lowpass_filter(altitude, 2, fs);
    residual = altitude - smoothed;
    
    fprintf('RMS noise: %.4f m\n', sqrt(mean(residual.^2)));
    fprintf('Filtered altitude range: [%.1f, %.1f] m\n', min(smoothed), max(smoothed));
    
    % FFT 분석
    spec = compute_fft(altitude - mean(altitude), fs);
    peaks = find_spectral_peaks(spec.freqs, spec.magnitude, 3);
    fprintf('Top dominant frequency: %.2f Hz\n', peaks.frequencies(1));
end
