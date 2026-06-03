% Phase 620: Signal Processor — GNU Octave
% SDACS digital signal processing for drone sensor data filtering

function signal_processor()
    fprintf('Phase 620: Signal Processor\n');

    % Generate noisy altitude signal
    Fs  = 100;   % sampling rate (Hz)
    T   = 10;    % duration (s)
    t   = 0:1/Fs:T-1/Fs;
    alt_true  = 60 + 5*sin(2*pi*0.2*t);
    noise     = 2 * randn(size(t));
    alt_noisy = alt_true + noise;

    % Low-pass FIR filter (moving average)
    window   = 10;
    weights  = ones(1, window) / window;
    alt_filt = filter(weights, 1, alt_noisy);

    % RMS noise before/after
    noise_before = rms(alt_noisy - alt_true);
    noise_after  = rms(alt_filt - alt_true);

    fprintf('  RMS noise before filter: %.3f m\n', noise_before);
    fprintf('  RMS noise after filter:  %.3f m\n', noise_after);
    fprintf('  SNR improvement:         %.1f dB\n', 20*log10(noise_before/noise_after));
end

function r = rms(x)
    r = sqrt(mean(x.^2));
end

signal_processor();
