% signal_processor.m
% Octave signal processing stub for swarm drone telemetry
% Applies basic filtering and FFT analysis to drone sensor streams

function result = signal_processor(raw_signal, sample_rate)
  % Validate inputs
  if nargin < 2
    sample_rate = 100;  % default 100 Hz
  end

  n = length(raw_signal);

  % Apply a simple low-pass moving-average filter (window = 5)
  window = 5;
  filtered = filter(ones(1, window) / window, 1, raw_signal);

  % Compute FFT for frequency-domain analysis
  fft_result = fft(filtered);
  freqs = (0:n-1) * (sample_rate / n);
  magnitude = abs(fft_result) / n;

  % Dominant frequency bin (exclude DC component)
  [~, peak_idx] = max(magnitude(2:floor(n/2)));
  dominant_freq = freqs(peak_idx + 1);

  % Signal statistics
  sig_mean = mean(filtered);
  sig_std  = std(filtered);
  sig_rms  = rms(filtered);

  result = struct(
    'filtered',       filtered,
    'freqs',          freqs,
    'magnitude',      magnitude,
    'dominant_freq',  dominant_freq,
    'mean',           sig_mean,
    'std',            sig_std,
    'rms',            sig_rms
  );

  fprintf('[signal_processor] sample_rate=%d Hz  dominant_freq=%.2f Hz  rms=%.4f\n', ...
          sample_rate, dominant_freq, sig_rms);
end
