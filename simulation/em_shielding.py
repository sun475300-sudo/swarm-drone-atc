"""
Phase 515: Electromagnetic Shielding
EMI 차폐 설계, 전자기 호환성(EMC), 간섭 분석.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class ShieldMaterial(Enum):
    COPPER = "copper"
    ALUMINUM = "aluminum"
    MU_METAL = "mu_metal"
    CARBON_FIBER = "carbon_fiber"
    CONDUCTIVE_PAINT = "conductive_paint"
    NONE = "none"


class EMISource(Enum):
    MOTOR = "motor"
    ESC = "esc"
    RADIO_TX = "radio_tx"
    GPS_JAMMER = "gps_jammer"
    POWER_LINE = "power_line"
    RADAR = "radar"
    LIGHTNING = "lightning"


class EMCStandard(Enum):
    MIL_STD_461G = "mil_std_461g"
    CISPR_32 = "cispr_32"
    FCC_PART15 = "fcc_part15"
    DO_160G = "do_160g"


@dataclass
class ShieldConfig:
    material: ShieldMaterial
    thickness_mm: float
    coverage_pct: float  # 0-100
    weight_g: float
    cost_usd: float


@dataclass
class EMIEvent:
    source: EMISource
    frequency_mhz: float
    power_dbm: float
    duration_s: float
    shielded_power_dbm: float = 0.0
    compliant: bool = True


@dataclass
class EMCReport:
    standard: EMCStandard
    emissions_pass: bool
    susceptibility_pass: bool
    margin_db: float
    worst_frequency_mhz: float


class ShieldingEffectiveness:
    """Calculate SE based on material and geometry."""

    def __init__(self):
        self.material_conductivity = {
            ShieldMaterial.COPPER: 5.8e7,
            ShieldMaterial.ALUMINUM: 3.5e7,
            ShieldMaterial.MU_METAL: 1.6e6,
            ShieldMaterial.CARBON_FIBER: 1e4,
            ShieldMaterial.CONDUCTIVE_PAINT: 1e3,
            ShieldMaterial.NONE: 0,
        }
        self.material_permeability = {
            ShieldMaterial.COPPER: 1.0,
            ShieldMaterial.ALUMINUM: 1.0,
            ShieldMaterial.MU_METAL: 20000.0,
            ShieldMaterial.CARBON_FIBER: 1.0,
            ShieldMaterial.CONDUCTIVE_PAINT: 1.0,
            ShieldMaterial.NONE: 1.0,
        }

    def compute_se(self, config: ShieldConfig, freq_mhz: float) -> float:
        if config.material == ShieldMaterial.NONE:
            return 0.0
        sigma = self.material_conductivity[config.material]
        mu_r = self.material_permeability[config.material]
        f = freq_mhz * 1e6
        t = config.thickness_mm * 1e-3

        skin_depth = 1 / np.sqrt(np.pi * f * 4 * np.pi * 1e-7 * mu_r * sigma + 1e-20)
        absorption = 8.686 * t / (skin_depth + 1e-10)
        reflection = 20 * np.log10(sigma / (16 * np.pi * f * 4 * np.pi * 1e-7 * mu_r + 1e-10) + 1)
        se = (absorption + reflection) * config.coverage_pct / 100
        return round(max(0, se), 1)


class EMIAnalyzer:
    """Analyze EMI impact on drone systems."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.events: List[EMIEvent] = []
        self.se_calc = ShieldingEffectiveness()

    def generate_threat(self, source: EMISource) -> EMIEvent:
        profiles = {
            EMISource.MOTOR: (0.1, 50, 30),
            EMISource.ESC: (1, 200, 25),
            EMISource.RADIO_TX: (400, 6000, 40),
            EMISource.GPS_JAMMER: (1575, 1580, 60),
            EMISource.POWER_LINE: (0.05, 0.06, 50),
            EMISource.RADAR: (1000, 10000, 70),
            EMISource.LIGHTNING: (0.001, 300, 80),
        }
        lo, hi, pwr = profiles.get(source, (1, 1000, 30))
        freq = self.rng.uniform(lo, hi)
        power = pwr + self.rng.standard_normal() * 5
        dur = self.rng.uniform(0.001, 10)
        return EMIEvent(source, round(freq, 3), round(power, 1), round(dur, 4))

    def assess_shielding(self, event: EMIEvent, shield: ShieldConfig) -> EMIEvent:
        se = self.se_calc.compute_se(shield, event.frequency_mhz)
        event.shielded_power_dbm = round(event.power_dbm - se, 1)
        event.compliant = event.shielded_power_dbm < 30
        self.events.append(event)
        return event


class EMShielding:
    """EM shielding design and analysis system."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.analyzer = EMIAnalyzer(seed)
        self.shields: Dict[str, ShieldConfig] = {}
        self.reports: List[EMCReport] = []

        self.shields["primary"] = ShieldConfig(
            ShieldMaterial.ALUMINUM, 0.5, 85, 50, 15)
        self.shields["secondary"] = ShieldConfig(
            ShieldMaterial.COPPER, 0.3, 60, 30, 25)

    def run_emc_test(self, shield_name: str = "primary",
                     standard: EMCStandard = EMCStandard.DO_160G) -> EMCReport:
        shield = self.shields.get(shield_name, ShieldConfig(ShieldMaterial.NONE, 0, 0, 0, 0))
        freqs = np.logspace(-1, 4, 50)  # 0.1 MHz to 10 GHz
        margins = []
        worst_freq = float(freqs[0])
        worst_margin = 100

        for f in freqs:
            se = self.analyzer.se_calc.compute_se(shield, f)
            margin = se - 20
            margins.append(margin)
            if margin < worst_margin:
                worst_margin = margin
                worst_freq = f

        report = EMCReport(standard,
                          all(m > 0 for m in margins),
                          worst_margin > -6,
                          round(worst_margin, 1), round(worst_freq, 3))
        self.reports.append(report)
        return report

    def optimize_shield(self, weight_budget_g: float = 100,
                        target_se_db: float = 40) -> ShieldConfig:
        best = None
        best_score = -1
        for mat in ShieldMaterial:
            if mat == ShieldMaterial.NONE:
                continue
            for thick in np.arange(0.1, 2.0, 0.1):
                density = {ShieldMaterial.COPPER: 8.96, ShieldMaterial.ALUMINUM: 2.7,
                          ShieldMaterial.MU_METAL: 8.7, ShieldMaterial.CARBON_FIBER: 1.6,
                          ShieldMaterial.CONDUCTIVE_PAINT: 1.2}.get(mat, 2.0)
                weight = density * thick * 100  # simplified
                if weight > weight_budget_g:
                    continue
                cfg = ShieldConfig(mat, thick, 90, round(weight, 1), round(thick * 50, 1))
                se = self.analyzer.se_calc.compute_se(cfg, 1000)
                if se >= target_se_db:
                    score = se / weight
                    if score > best_score:
                        best_score = score
                        best = cfg
        return best or ShieldConfig(ShieldMaterial.ALUMINUM, 1.0, 90, 270, 50)

    def summary(self) -> Dict:
        return {
            "shields": len(self.shields),
            "emi_events": len(self.analyzer.events),
            "emc_tests": len(self.reports),
            "compliant_events": sum(1 for e in self.analyzer.events if e.compliant),
        }
