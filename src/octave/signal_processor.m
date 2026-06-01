% Signal Processor — GNU Octave for SDACS sensor signal processing
% Phase 620

function result = signal_processor_demo()
  % Generate a noisy test signal
  fs = 1000;          % sampling frequency Hz
  t  = 0:1/fs:1-1/fs; % 1 second
  f1 = 10;            % 10 Hz signal
  f2 = 50;            % 50 Hz noise

  clean_signal = sin(2*pi*f1*t);
  noise = 0.3 * sin(2*pi*f2*t) + 0.1 * randn(size(t));
  noisy_signal = clean_signal + noise;

  % Apply low-pass FIR filter
  filtered = lowpass_filter(noisy_signal, f1*3, fs);

  % Compute FFT
  [freq, mag] = compute_fft(noisy_signal, fs);

  % SNR before and after filtering
  snr_before = compute_snr(clean_signal, noisy_signal - clean_signal);
  snr_after  = compute_snr(clean_signal, filtered - clean_signal);

  result = struct(
    'snr_before_db', snr_before,
    'snr_after_db',  snr_after,
    'improvement_db', snr_after - snr_before,
    'samples', length(t),
    'fs_hz',   fs
  );

  printf('Signal Processor Results:\n');
  printf('  SNR before: %.2f dB\n', snr_before);
  printf('  SNR after:  %.2f dB\n', snr_after);
  printf('  Improvement: %.2f dB\n', snr_after - snr_before);
end

function filtered = lowpass_filter(signal, cutoff_hz, fs)
  % Simple moving average as crude low-pass filter
  N = max(1, round(fs / cutoff_hz / 2));
  kernel = ones(1, N) / N;
  filtered = conv(signal, kernel, 'same');
end

function [freq, mag] = compute_fft(signal, fs)
  N    = length(signal);
  Y    = fft(signal);
  mag  = abs(Y(1:N/2+1)) * 2 / N;
  freq = (0:N/2) * fs / N;
end

function snr = compute_snr(signal, noise)
  sig_power   = mean(signal .^ 2);
  noise_power = mean(noise  .^ 2);
  if noise_power < 1e-12
    snr = Inf;
  else
    snr = 10 * log10(sig_power / noise_power);
  end
end

function rms = compute_rms(signal)
  rms = sqrt(mean(signal .^ 2));
end

function out = bandpass_filter(signal, low_hz, high_hz, fs)
  % Difference of two moving averages as crude bandpass
  low_pass  = lowpass_filter(signal, high_hz, fs);
  high_pass = low_pass - lowpass_filter(signal, low_hz, fs);
  out = high_pass;
end

% Run demo if called directly
if nargin == 0 && ~nargout
  result = signal_processor_demo();
end
