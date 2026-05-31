% Signal Processor — SDACS Phase 620
function result = process_telemetry(data)
  % Low-pass filter for drone telemetry
  fs = 100;  % sampling rate Hz
  fc = 10;   % cutoff Hz
  [b, a] = butter(4, fc/(fs/2), 'low');
  result = filter(b, a, data);
end

function snr = compute_snr(signal, noise)
  snr = 10 * log10(var(signal) / var(noise));
end
