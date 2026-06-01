% Signal Processor — Octave module for Phase 620
% Digital signal processing utilities for drone telemetry and communication signals.

% ===== Configuration =====

FS = 1000;          % sampling frequency (Hz)
N  = 2048;          % number of samples
T  = N / FS;        % total time window (seconds)

t = (0:N-1) / FS;   % time vector

% ===== Signal Generation =====

% Generate composite drone telemetry signal
% Altitude oscillation at 0.5 Hz, noise at higher frequencies
altitude_signal = 80 + 5 * sin(2 * pi * 0.5 * t) + ...
                  2 * sin(2 * pi * 2.0 * t) + ...
                  0.5 * randn(1, N);

% Battery drain signal (slow decay + ripple)
battery_signal = 90 - 10 * (t / T) + 0.3 * sin(2 * pi * 5 * t) + ...
                 0.1 * randn(1, N);

% Communication RSSI signal
rssi_signal = -70 + 5 * sin(2 * pi * 0.1 * t) + 3 * randn(1, N);

% ===== Windowing Functions =====

function w = hann_window(n)
  % Hann window for spectral leakage reduction
  w = 0.5 * (1 - cos(2 * pi * (0:n-1) / (n-1)));
end

function w = hamming_window(n)
  % Hamming window
  w = 0.54 - 0.46 * cos(2 * pi * (0:n-1) / (n-1));
end

% ===== FFT Spectrum Analysis =====

function [freqs, magnitude_db] = compute_spectrum(signal, fs)
  % Compute single-sided amplitude spectrum in dB
  n = length(signal);
  w = hann_window(n);
  X = fft(signal .* w);
  X = X(1:floor(n/2)+1);
  mag = abs(X) / n;
  mag(2:end-1) = 2 * mag(2:end-1);  % double-sided to single-sided
  magnitude_db = 20 * log10(max(mag, 1e-10));
  freqs = (0:floor(n/2)) * fs / n;
end

% ===== Low-Pass Filter (Moving Average) =====

function filtered = moving_average_filter(signal, window_size)
  % Simple FIR low-pass filter using moving average
  n = length(signal);
  filtered = zeros(1, n);
  half_w = floor(window_size / 2);
  for i = 1:n
    lo = max(1, i - half_w);
    hi = min(n, i + half_w);
    filtered(i) = mean(signal(lo:hi));
  end
end

% ===== Median Filter (Spike Removal) =====

function filtered = median_filter(signal, window_size)
  n = length(signal);
  filtered = zeros(1, n);
  half_w = floor(window_size / 2);
  for i = 1:n
    lo = max(1, i - half_w);
    hi = min(n, i + half_w);
    filtered(i) = median(signal(lo:hi));
  end
end

% ===== SNR Estimation =====

function snr_db = estimate_snr(signal, noise_floor_db)
  % Estimate SNR relative to a noise floor
  signal_power_db = 10 * log10(var(signal));
  snr_db = signal_power_db - noise_floor_db;
end

% ===== Cross-Correlation Analysis =====

function [lags, xcorr_vals] = compute_xcorr(sig1, sig2, max_lag)
  % Compute normalized cross-correlation up to max_lag samples
  n = length(sig1);
  lags = -max_lag:max_lag;
  xcorr_vals = zeros(1, length(lags));
  norm_factor = sqrt(sum(sig1.^2) * sum(sig2.^2));
  for k = 1:length(lags)
    lag = lags(k);
    if lag >= 0
      overlap = sig1(1:n-lag) .* sig2(lag+1:n);
    else
      overlap = sig1(1-lag:n) .* sig2(1:n+lag);
    end
    xcorr_vals(k) = sum(overlap) / norm_factor;
  end
end

% ===== Statistics =====

function stats = signal_stats(signal, name)
  stats.name    = name;
  stats.mean    = mean(signal);
  stats.std     = std(signal);
  stats.min     = min(signal);
  stats.max     = max(signal);
  stats.rms     = sqrt(mean(signal.^2));
  stats.peak2pk = max(signal) - min(signal);
  stats.snr_db  = estimate_snr(signal, -30);
end

% ===== Main Processing =====

fprintf('Phase 620: Signal Processor\n');
fprintf('Sampling rate: %d Hz | Samples: %d | Window: %.2f s\n', FS, N, T);

% Apply filters
filtered_alt    = moving_average_filter(altitude_signal, 21);
filtered_rssi   = median_filter(rssi_signal, 11);
filtered_bat    = moving_average_filter(battery_signal, 51);

% Compute spectra
[freqs_alt, mag_alt] = compute_spectrum(altitude_signal, FS);

% Print statistics
fprintf('\n=== Signal Statistics ===\n');
s1 = signal_stats(altitude_signal, 'altitude_m');
fprintf('Altitude: mean=%.2f | std=%.2f | RMS=%.2f | SNR=%.1f dB\n', ...
        s1.mean, s1.std, s1.rms, s1.snr_db);

s2 = signal_stats(battery_signal, 'battery_pct');
fprintf('Battery:  mean=%.2f | std=%.2f | peak2pk=%.2f\n', ...
        s2.mean, s2.std, s2.peak2pk);

s3 = signal_stats(rssi_signal, 'rssi_dbm');
fprintf('RSSI:     mean=%.2f | std=%.2f | SNR=%.1f dB\n', ...
        s3.mean, s3.std, s3.snr_db);

% Filter performance
noise_reduction = std(altitude_signal) - std(filtered_alt);
fprintf('\nFilter noise reduction (altitude): %.4f\n', noise_reduction);

% Peak frequency
[~, peak_idx] = max(mag_alt(2:end));  % skip DC
fprintf('Peak spectral frequency: %.2f Hz\n', freqs_alt(peak_idx + 1));

fprintf('Signal processing complete.\n');
