"""
Phase 504: Hyperspectral Sensor Fusion
초분광 센서 데이터 처리, 스펙트럼 분류, 환경 매핑.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class SpectralBand(Enum):
    VISIBLE = (400, 700)      # nm
    NIR = (700, 1000)         # Near-IR
    SWIR = (1000, 2500)       # Short-Wave IR
    MWIR = (3000, 5000)       # Mid-Wave IR
    LWIR = (8000, 14000)      # Long-Wave IR


class TerrainType(Enum):
    VEGETATION = "vegetation"
    WATER = "water"
    URBAN = "urban"
    SOIL = "soil"
    CONCRETE = "concrete"
    METAL = "metal"
    UNKNOWN = "unknown"


@dataclass
class SpectralSignature:
    terrain: TerrainType
    bands: np.ndarray  # reflectance per band
    wavelengths: np.ndarray


@dataclass
class HyperspectralPixel:
    x: int
    y: int
    spectrum: np.ndarray
    classified: TerrainType = TerrainType.UNKNOWN
    confidence: float = 0.0


class SpectralLibrary:
    """Reference spectral signatures for classification."""

    def __init__(self, n_bands: int = 64, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_bands = n_bands
        self.wavelengths = np.linspace(400, 2500, n_bands)
        self.signatures: Dict[TerrainType, np.ndarray] = {}
        self._init_signatures()

    def _init_signatures(self):
        n = self.n_bands
        self.signatures[TerrainType.VEGETATION] = np.concatenate([
            np.linspace(0.05, 0.1, n // 4),
            np.linspace(0.4, 0.5, n // 4),
            np.linspace(0.3, 0.2, n // 4),
            np.linspace(0.2, 0.15, n - 3 * (n // 4))])
        self.signatures[TerrainType.WATER] = np.concatenate([
            np.linspace(0.1, 0.05, n // 2),
            np.linspace(0.02, 0.01, n - n // 2)])
        self.signatures[TerrainType.URBAN] = np.full(n, 0.25) + self.rng.standard_normal(n) * 0.02
        self.signatures[TerrainType.SOIL] = np.linspace(0.1, 0.3, n) + self.rng.standard_normal(n) * 0.01
        self.signatures[TerrainType.CONCRETE] = np.full(n, 0.35) + self.rng.standard_normal(n) * 0.015
        self.signatures[TerrainType.METAL] = np.full(n, 0.6) + self.rng.standard_normal(n) * 0.03


class SpectralClassifier:
    """Spectral Angle Mapper (SAM) classifier."""

    def __init__(self, library: SpectralLibrary):
        self.library = library

    def classify(self, spectrum: np.ndarray) -> Tuple[TerrainType, float]:
        best_type = TerrainType.UNKNOWN
        best_angle = np.pi
        for terrain, ref in self.library.signatures.items():
            cos_angle = np.dot(spectrum, ref) / (np.linalg.norm(spectrum) * np.linalg.norm(ref) + 1e-10)
            angle = np.arccos(np.clip(cos_angle, -1, 1))
            if angle < best_angle:
                best_angle = angle
                best_type = terrain
        confidence = 1.0 - best_angle / np.pi
        return best_type, round(float(confidence), 4)


class HyperspectralSensor:
    """Airborne hyperspectral imaging sensor."""

    def __init__(self, n_bands: int = 64, resolution: int = 32, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_bands = n_bands
        self.resolution = resolution
        self.library = SpectralLibrary(n_bands, seed)
        self.classifier = SpectralClassifier(self.library)
        self.scans: List[np.ndarray] = []

    def capture(self, altitude_m: float = 100) -> List[HyperspectralPixel]:
        snr_factor = max(0.5, 1.0 - altitude_m / 500)
        pixels = []
        terrain_map = self.rng.choice(list(TerrainType)[:-1], (self.resolution, self.resolution))

        for x in range(self.resolution):
            for y in range(self.resolution):
                terrain = terrain_map[x, y]
                base = self.library.signatures.get(terrain, np.zeros(self.n_bands))
                noise = self.rng.standard_normal(self.n_bands) * 0.05 / snr_factor
                spectrum = np.clip(base + noise, 0, 1)
                classified, conf = self.classifier.classify(spectrum)
                pixels.append(HyperspectralPixel(x, y, spectrum, classified, conf))

        self.scans.append(np.array([p.spectrum for p in pixels]))
        return pixels

    def generate_map(self, pixels: List[HyperspectralPixel]) -> Dict[str, int]:
        counts = {}
        for p in pixels:
            key = p.classified.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def ndvi(self, pixels: List[HyperspectralPixel]) -> List[float]:
        """Normalized Difference Vegetation Index."""
        red_idx = self.n_bands // 4
        nir_idx = self.n_bands // 2
        ndvi_values = []
        for p in pixels:
            red = p.spectrum[red_idx]
            nir = p.spectrum[nir_idx]
            val = (nir - red) / (nir + red + 1e-10)
            ndvi_values.append(round(float(val), 4))
        return ndvi_values

    def summary(self) -> Dict:
        return {
            "bands": self.n_bands,
            "resolution": self.resolution,
            "scans": len(self.scans),
            "library_size": len(self.library.signatures),
        }
