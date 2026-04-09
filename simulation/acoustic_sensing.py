"""
Phase 338: Acoustic Sensing System
FFT 스펙트럼 분석 + 빔포밍 + DoA(Direction of Arrival) 추정.
드론 프로펠러 소음 감지 및 위치 추정.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class SignalType(Enum):
    PROPELLER = "propeller"
    ENGINE = "engine"
    WIND = "wind"
    SPEECH = "speech"
    UNKNOWN = "unknown"


class DetectionStatus(Enum):
    DETECTED = "detected"
    TRACKING = "tracking"
    LOST = "lost"


@dataclass
class Microphone:
    mic_id: int
    x: float
    y: float
    z: float


@dataclass
class AcousticSignal:
    signal_id: str
    samples: np.ndarray
    sample_rate: int
    timestamp: float
    mic_id: int


@dataclass
class SpectralPeak:
    frequency: float
    magnitude: float
    phase: float


@dataclass
class DoAEstimate:
    azimuth_deg: float
    elevation_deg: float
    confidence: float
    source_type: SignalType
    distance_estimate: float


@dataclass
class AcousticDetection:
    detection_id: str
    doa: DoAEstimate
    status: DetectionStatus
    timestamp: float
    spectral_peaks: List[SpectralPeak]


class FFTAnalyzer:
    """FFT-based spectral analysis engine."""

    def __init__(self, sample_rate: int = 44100, fft_size: int = 2048):
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.freq_resolution = sample_rate / fft_size

    def compute_spectrum(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        n = min(len(signal), self.fft_size)
        windowed = signal[:n] * np.hanning(n)
        spectrum = np.fft.rfft(windowed, n=self.fft_size)
        magnitudes = np.abs(spectrum) / n
        freqs = np.fft.rfftfreq(self.fft_size, 1.0 / self.sample_rate)
        return freqs, magnitudes

    def find_peaks(self, freqs: np.ndarray, magnitudes: np.ndarray,
                   threshold: float = 0.01, max_peaks: int = 10) -> List[SpectralPeak]:
        peaks = []
        for i in range(1, len(magnitudes) - 1):
            if (magnitudes[i] > magnitudes[i-1] and
                magnitudes[i] > magnitudes[i+1] and
                magnitudes[i] > threshold):
                peaks.append(SpectralPeak(
                    frequency=float(freqs[i]),
                    magnitude=float(magnitudes[i]),
                    phase=0.0
                ))
        peaks.sort(key=lambda p: -p.magnitude)
        return peaks[:max_peaks]

    def classify_signal(self, peaks: List[SpectralPeak]) -> SignalType:
        if not peaks:
            return SignalType.UNKNOWN

        dominant_freq = peaks[0].frequency
        if 50 <= dominant_freq <= 500:
            harmonics = sum(1 for p in peaks[1:] if
                          abs(p.frequency / dominant_freq - round(p.frequency / dominant_freq)) < 0.1)
            if harmonics >= 2:
                return SignalType.PROPELLER
            return SignalType.ENGINE
        elif dominant_freq < 50:
            return SignalType.WIND
        elif 300 <= dominant_freq <= 3400:
            return SignalType.SPEECH
        return SignalType.UNKNOWN


class Beamformer:
    """Delay-and-sum beamformer for microphone array."""

    SPEED_OF_SOUND = 343.0  # m/s

    def __init__(self, mics: List[Microphone]):
        self.mics = mics
        self.n_mics = len(mics)
        self.positions = np.array([[m.x, m.y, m.z] for m in mics])

    def compute_steering_vector(self, azimuth_deg: float,
                                 elevation_deg: float, freq: float) -> np.ndarray:
        az = np.radians(azimuth_deg)
        el = np.radians(elevation_deg)
        direction = np.array([
            np.cos(el) * np.cos(az),
            np.cos(el) * np.sin(az),
            np.sin(el)
        ])
        delays = self.positions @ direction / self.SPEED_OF_SOUND
        return np.exp(-2j * np.pi * freq * delays)

    def beamform_power(self, signals: np.ndarray, freq: float,
                       azimuth_deg: float, elevation_deg: float) -> float:
        sv = self.compute_steering_vector(azimuth_deg, elevation_deg, freq)
        if signals.ndim == 1:
            signals = signals.reshape(self.n_mics, -1)
        fft_data = np.fft.rfft(signals, axis=1)
        freq_idx = int(freq / (44100 / signals.shape[1]))
        freq_idx = min(freq_idx, fft_data.shape[1] - 1)
        x = fft_data[:, freq_idx]
        output = np.abs(np.conj(sv) @ x) ** 2
        return float(output)

    def scan_doa(self, signals: np.ndarray, freq: float,
                 az_range: Tuple[float, float] = (-180, 180),
                 el_range: Tuple[float, float] = (-30, 90),
                 step: float = 5.0) -> DoAEstimate:
        best_power = 0.0
        best_az = 0.0
        best_el = 0.0

        for az in np.arange(az_range[0], az_range[1], step):
            for el in np.arange(el_range[0], el_range[1], step):
                power = self.beamform_power(signals, freq, az, el)
                if power > best_power:
                    best_power = power
                    best_az = az
                    best_el = el

        confidence = min(1.0, best_power / max(1e-10, best_power + 0.1))
        return DoAEstimate(
            azimuth_deg=best_az, elevation_deg=best_el,
            confidence=confidence, source_type=SignalType.UNKNOWN,
            distance_estimate=0.0
        )


class AcousticSensingSystem:
    """Complete acoustic sensing pipeline."""

    def __init__(self, n_mics: int = 4, array_radius: float = 0.5,
                 sample_rate: int = 44100, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.sample_rate = sample_rate

        mics = []
        for i in range(n_mics):
            angle = 2 * np.pi * i / n_mics
            mics.append(Microphone(i, array_radius * np.cos(angle),
                                    array_radius * np.sin(angle), 0))
        self.mics = mics
        self.fft = FFTAnalyzer(sample_rate)
        self.beamformer = Beamformer(mics)
        self.detections: List[AcousticDetection] = []
        self._det_counter = 0

    def generate_test_signal(self, freq: float, duration: float = 0.1,
                             snr_db: float = 20.0,
                             azimuth_deg: float = 0) -> np.ndarray:
        n_samples = int(duration * self.sample_rate)
        t = np.arange(n_samples) / self.sample_rate
        signals = np.zeros((len(self.mics), n_samples))
        for i, mic in enumerate(self.mics):
            delay = mic.x * np.cos(np.radians(azimuth_deg)) / 343.0
            phase = 2 * np.pi * freq * (t - delay)
            clean = np.sin(phase)
            noise_power = 10 ** (-snr_db / 10)
            noise = self.rng.standard_normal(n_samples) * np.sqrt(noise_power)
            signals[i] = clean + noise
        return signals

    def process(self, signals: np.ndarray, timestamp: float = 0.0) -> Optional[AcousticDetection]:
        if signals.ndim == 1:
            freqs, mags = self.fft.compute_spectrum(signals)
            peaks = self.fft.find_peaks(freqs, mags)
            sig_type = self.fft.classify_signal(peaks)
            doa = DoAEstimate(0, 0, 0.5, sig_type, 0)
        else:
            freqs, mags = self.fft.compute_spectrum(signals[0])
            peaks = self.fft.find_peaks(freqs, mags)
            sig_type = self.fft.classify_signal(peaks)

            if peaks:
                doa = self.beamformer.scan_doa(signals, peaks[0].frequency, step=10.0)
                doa.source_type = sig_type
            else:
                doa = DoAEstimate(0, 0, 0, sig_type, 0)

        if not peaks or doa.confidence < 0.1:
            return None

        self._det_counter += 1
        detection = AcousticDetection(
            detection_id=f"ACO-{self._det_counter:06d}",
            doa=doa,
            status=DetectionStatus.DETECTED,
            timestamp=timestamp,
            spectral_peaks=peaks[:5]
        )
        self.detections.append(detection)
        return detection

    def summary(self) -> Dict:
        type_counts: Dict[str, int] = {}
        for d in self.detections:
            t = d.doa.source_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        return {
            "microphones": len(self.mics),
            "total_detections": len(self.detections),
            "signal_types": type_counts,
            "sample_rate": self.sample_rate,
        }


if __name__ == "__main__":
    system = AcousticSensingSystem(n_mics=4, seed=42)

    for freq in [150, 300, 600]:
        signals = system.generate_test_signal(freq, duration=0.05, azimuth_deg=45)
        det = system.process(signals, timestamp=freq / 100.0)
        if det:
            print(f"Detected {det.doa.source_type.value} @ "
                  f"az={det.doa.azimuth_deg:.0f}° "
                  f"conf={det.doa.confidence:.2f}")

    print(f"Summary: {system.summary()}")
