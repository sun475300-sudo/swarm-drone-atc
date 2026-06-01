% Phase 620 — Octave Signal Processor for SDACS telemetry
% Digital signal processing for drone sensor data filtering

function result = butter_lowpass(signal, cutoff_hz, sample_rate)
  % Apply 2nd-order Butterworth low-pass filter
  nyq = sample_rate / 2;
  wn  = cutoff_hz / nyq;
  [b, a] = butter(2, wn, 'low');
  result = filter(b, a, signal);
end

function result = moving_average(signal, window)
  % Simple moving average filter
  n = length(signal);
  result = zeros(1, n);
  for i = 1:n
    lo = max(1, i - floor(window/2));
    hi = min(n, i + floor(window/2));
    result(i) = mean(signal(lo:hi));
  end
end

function [freqs, magnitudes] = compute_fft(signal, sample_rate)
  % Compute single-sided amplitude spectrum
  n = length(signal);
  Y = fft(signal);
  P2 = abs(Y / n);
  P1 = P2(1:floor(n/2)+1);
  P1(2:end-1) = 2 * P1(2:end-1);
  freqs = sample_rate * (0:(floor(n/2))) / n;
  magnitudes = P1;
end

function [mean_v, std_v, rms_v] = signal_stats(signal)
  % Basic statistics for a sensor signal
  mean_v = mean(signal);
  std_v  = std(signal);
  rms_v  = sqrt(mean(signal .^ 2));
end

function filtered = kalman_1d(measurements, Q, R)
  % Simple 1D Kalman filter for noisy sensor readings
  % Q: process noise, R: measurement noise
  n = length(measurements);
  filtered = zeros(1, n);
  x = measurements(1);
  P = 1.0;
  for i = 1:n
    % Predict
    x_pred = x;
    P_pred = P + Q;
    % Update
    K = P_pred / (P_pred + R);
    x = x_pred + K * (measurements(i) - x_pred);
    P = (1 - K) * P_pred;
    filtered(i) = x;
  end
end
