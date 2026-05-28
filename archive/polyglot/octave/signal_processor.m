% Phase 620: Signal Processor — Octave/MATLAB FFT Analysis
% 드론 센서 신호 FFT 분석

function results = signal_processor(signal_data, sample_rate)
    % SIGNAL_PROCESSOR Analyze drone sensor signals using FFT
    %
    % Parameters:
    %   signal_data - time-domain signal vector
    %   sample_rate - sampling frequency in Hz
    %
    % Returns:
    %   results - struct with frequency analysis

    if nargin < 2
        sample_rate = 1000;  % default 1kHz
    end

    N = length(signal_data);
    t = (0:N-1) / sample_rate;

    % ── FFT Analysis ──
    Y = fft(signal_data);
    P2 = abs(Y / N);
    P1 = P2(1:floor(N/2)+1);
    P1(2:end-1) = 2 * P1(2:end-1);
    f = sample_rate * (0:floor(N/2)) / N;

    % ── Peak Detection ──
    [peak_vals, peak_locs] = findpeaks(P1, 'MinPeakHeight', max(P1) * 0.1);
    peak_freqs = f(peak_locs);

    % ── Power Spectral Density ──
    psd = (abs(Y).^2) / (N * sample_rate);
    psd_one_sided = psd(1:floor(N/2)+1);
    psd_one_sided(2:end-1) = 2 * psd_one_sided(2:end-1);
    total_power = sum(psd_one_sided);

    % ── Band Power ──
    low_band = sum(psd_one_sided(f < 10));
    mid_band = sum(psd_one_sided(f >= 10 & f < 100));
    high_band = sum(psd_one_sided(f >= 100));

    % ── Signal Statistics ──
    signal_mean = mean(signal_data);
    signal_std = std(signal_data);
    signal_rms = sqrt(mean(signal_data.^2));
    snr_estimate = 10 * log10(signal_rms^2 / signal_std^2);

    % ── Moving Average Filter ──
    window_size = min(50, floor(N/10));
    if window_size > 0
        filtered = movmean(signal_data, window_size);
    else
        filtered = signal_data;
    end

    % ── Results ──
    results.frequencies = f;
    results.spectrum = P1;
    results.psd = psd_one_sided;
    results.peak_frequencies = peak_freqs;
    results.peak_amplitudes = peak_vals;
    results.total_power = total_power;
    results.band_power.low = low_band;
    results.band_power.mid = mid_band;
    results.band_power.high = high_band;
    results.stats.mean = signal_mean;
    results.stats.std = signal_std;
    results.stats.rms = signal_rms;
    results.stats.snr_db = snr_estimate;
    results.filtered = filtered;
    results.sample_rate = sample_rate;
    results.n_samples = N;

end

% ── Helper: Generate test signal ──
function sig = generate_test_signal(duration, sample_rate)
    t = 0:1/sample_rate:duration;
    % 50Hz drone motor + 200Hz vibration + noise
    sig = sin(2*pi*50*t) + 0.5*sin(2*pi*200*t) + 0.3*randn(size(t));
end

% ── Helper: Detect anomalies in spectrum ──
function anomalies = detect_spectral_anomalies(results, threshold_db)
    if nargin < 2
        threshold_db = 20;
    end
    mean_power = mean(results.psd);
    threshold = mean_power * 10^(threshold_db/10);
    anomaly_idx = find(results.psd > threshold);
    anomalies.frequencies = results.frequencies(anomaly_idx);
    anomalies.powers = results.psd(anomaly_idx);
    anomalies.count = length(anomaly_idx);
end
