% SDACS Phase 620 — GNU Octave DSP signal processing for ATC radar
function filtered = low_pass_filter(signal, cutoff_hz, sample_rate)
  nyquist = sample_rate / 2;
  normalized_cutoff = cutoff_hz / nyquist;
  [b, a] = butter(4, normalized_cutoff, 'low');
  filtered = filter(b, a, signal);
end
function spectrum = compute_fft(signal, sample_rate)
  N = length(signal);
  spectrum = abs(fft(signal)) / N;
  spectrum = spectrum(1:floor(N/2)+1);
end
