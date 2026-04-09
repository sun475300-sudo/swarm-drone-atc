"""
Energy Harvesting Manager
Phase 355 - Solar MPPT, RF Harvesting, Power Management
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum


class EnergySource(Enum):
    SOLAR = "solar"
    RF = "rf"
    BATTERY = "battery"
    GRID = "grid"


class HarvestingMode(Enum):
    MPPT = "mppt"
    CCCV = "cccv"
    FLOAT = "float"
    OFF = "off"


@dataclass
class SolarPanel:
    area_m2: float
    efficiency: float = 0.22
    temperature: float = 25.0
    voltage: float = 18.0
    current: float = 0.0
    power: float = 0.0

    def calculate_power(self, irradiance: float, temperature: float) -> float:
        temp_coeff = -0.004 * (temperature - 25)
        self.power = self.area_m2 * irradiance * self.efficiency * (1 + temp_coeff)
        self.current = self.power / self.voltage
        return self.power


@dataclass
class RFHarvester:
    sensitivity_dbm: float = -20.0
    antenna_gain_dbi: float = 3.0
    frequency_mhz: float = 915.0
    efficiency: float = 0.65
    received_power_dbm: float = -30.0
    harvested_power_mw: float = 0.0

    def calculate_harvested_power(
        self, tx_power_dbm: float, distance_m: float
    ) -> float:
        freq = self.frequency_mhz
        wavelength = 300 / freq

        path_loss = 20 * np.log10(4 * np.pi * distance_m / wavelength)
        received_power = tx_power_dbm + self.antenna_gain_dbi - path_loss

        self.received_power_dbm = received_power

        if received_power < self.sensitivity_dbm:
            self.harvested_power_mw = 0
            return 0

        power_mw = 10 ** ((received_power - 30) / 10)
        self.harvested_power_mw = power_mw * self.efficiency

        return self.harvested_power_mw


@dataclass
class Battery:
    capacity_wh: float
    current_charge_wh: float
    voltage: float = 12.0
    max_charge_rate_w: float = 50.0
    max_discharge_rate_w: float = 100.0
    efficiency: float = 0.95
    soc: float = 0.5
    temperature: float = 25.0
    cycles: int = 0

    def __post_init__(self):
        self.soc = self.current_charge_wh / self.capacity_wh

    def charge(self, power_w: float, delta_time_h: float) -> float:
        actual_power = min(power_w, self.max_charge_rate_w)
        energy_in = actual_power * delta_time_h
        energy_stored = energy_in * self.efficiency

        new_charge = min(self.current_charge_wh + energy_stored, self.capacity_wh)
        self.current_charge_wh = new_charge
        self.soc = new_charge / self.capacity_wh

        return actual_power

    def discharge(self, power_w: float, delta_time_h: float) -> float:
        actual_power = min(power_w, self.max_discharge_rate_w)
        energy_out = actual_power * delta_time_h
        energy_used = energy_out / self.efficiency

        new_charge = max(self.current_charge_wh - energy_used, 0)
        self.current_charge_wh = new_charge
        self.soc = new_charge / self.capacity_wh

        return actual_power

    def get_soc_percent(self) -> float:
        return self.soc * 100


class MPPTController:
    def __init__(self, panel: SolarPanel):
        self.panel = panel
        self.voc = panel.voltage * 1.2
        self.imp = panel.current
        self.vmp = panel.voltage
        self.tracking_mode = "P&O"
        self.step_size = 0.5

    def perturb_and_observe(
        self, irradiance: float, temperature: float
    ) -> Tuple[float, float]:
        v_prev = self.panel.voltage
        p_prev = self.panel.power

        self.panel.voltage += self.step_size
        p_new = self.panel.calculate_power(irradiance, temperature)

        if p_new > p_prev:
            self.panel.voltage += self.step_size
        else:
            self.panel.voltage -= 2 * self.step_size

        self.panel.voltage = np.clip(self.panel.voltage, 0, self.voc)

        return self.panel.voltage, self.panel.power

    def incremental_conductance(
        self, irradiance: float, temperature: float
    ) -> Tuple[float, float]:
        dv = self.step_size
        dp = self.panel.power - (self.panel.current * self.panel.voltage)

        if abs(dv) < 0.001:
            return self.panel.voltage, self.panel.power

        delta_i = dp / dv

        if delta_i > 0:
            self.panel.voltage += self.step_size
        elif delta_i < 0:
            self.panel.voltage -= self.step_size

        self.panel.voltage = np.clip(self.panel.voltage, 0, self.voc)
        p_new = self.panel.calculate_power(irradiance, temperature)

        return self.panel.voltage, p_new


class EnergyManagementSystem:
    def __init__(self):
        self.solar_panel = SolarPanel(area_m2=0.1, efficiency=0.22)
        self.rf_harvester = RFHarvester()
        self.battery = Battery(capacity_wh=500, current_charge_wh=250)
        self.mppt = MPPTController(self.solar_panel)

        self.power_budget: Dict[str, float] = {}
        self.harvest_history: List[Dict] = []
        self.total_harvested_wh: float = 0.0

    def calculate_available_power(
        self,
        irradiance: float,
        temperature: float,
        rf_tx_power_dbm: float,
        rf_distance_m: float,
    ) -> Dict[str, float]:
        solar_power = self.solar_panel.calculate_power(irradiance, temperature)
        rf_power_mw = self.rf_harvester.calculate_harvested_power(
            rf_tx_power_dbm, rf_distance_m
        )
        rf_power_w = rf_power_mw / 1000

        return {
            "solar_w": solar_power,
            "rf_w": rf_power_w,
            "total_harvest_w": solar_power + rf_power_w,
        }

    def power_allocation(
        self, required_power: float, available_power: Dict[str, float]
    ) -> Dict[str, float]:
        solar_available = available_power["solar_w"]
        rf_available = available_power["rf_w"]
        battery_available = self.battery.max_discharge_rate_w * self.battery.soc

        allocation = {
            "solar_used_w": 0,
            "rf_used_w": 0,
            "battery_used_w": 0,
            "grid_needed_w": 0,
        }

        remaining = required_power

        solar_used = min(remaining, solar_available)
        allocation["solar_used_w"] = solar_used
        remaining -= solar_used

        rf_used = min(remaining, rf_available)
        allocation["rf_used_w"] = rf_used
        remaining -= rf_used

        if remaining > 0 and self.battery.soc > 0.2:
            battery_used = min(remaining, battery_available)
            allocation["battery_used_w"] = battery_used
            remaining -= battery_used

        allocation["grid_needed_w"] = max(0, remaining)

        return allocation

    def update_battery(
        self, charge_power: float, discharge_power: float, delta_time_h: float = 0.001
    ):
        net_power = charge_power - discharge_power

        if net_power > 0:
            self.battery.charge(net_power, delta_time_h)
        elif net_power < 0:
            self.battery.discharge(abs(net_power), delta_time_h)

    def simulate_operation(self, duration_h: float = 1.0, time_step_s: float = 1.0):
        time_step_h = time_step_s / 3600
        num_steps = int(duration_h * 3600 / time_step_s)

        print(f"=== Energy Harvesting Simulation ({duration_h}h) ===")

        for step in range(num_steps):
            hour = step * time_step_s / 3600

            irradiance = 1000 * np.sin(hour * np.pi / 12) if 0 <= hour <= 12 else 0
            temperature = 25 + 10 * np.sin(hour * np.pi / 12)

            rf_tx_power = np.random.uniform(20, 30)
            rf_distance = np.random.uniform(1, 10)

            available = self.calculate_available_power(
                irradiance, temperature, rf_tx_power, rf_distance
            )

            required_power = 20 + 10 * np.sin(hour)
            allocation = self.power_allocation(required_power, available)

            charge_power = allocation["solar_used_w"] + allocation["rf_used_w"]
            discharge_power = allocation["battery_used_w"] + allocation["grid_needed_w"]

            self.update_battery(charge_power, discharge_power, time_step_h)

            self.total_harvested_wh += (
                allocation["solar_used_w"] + allocation["rf_used_w"]
            ) * time_step_h

            if step % 3600 == 0:
                print(
                    f"Hour {hour:.0f}: Solar={available['solar_w']:.1f}W, RF={available['rf_w']:.2f}W, "
                    f"Battery SoC={self.battery.get_soc_percent():.1f}%"
                )

        print(f"\n=== Summary ===")
        print(f"Total Harvested: {self.total_harvested_wh:.2f} Wh")
        print(f"Final Battery SoC: {self.battery.get_soc_percent():.1f}%")

        return {
            "total_harvested_wh": self.total_harvested_wh,
            "final_soc_percent": self.battery.get_soc_percent(),
            "num_cycles": self.battery.cycles,
        }


class DroneEnergyOptimizer:
    def __init__(self, num_drones: int = 10):
        self.drones: Dict[str, EnergyManagementSystem] = {}
        self.num_drones = num_drones
        self._init_drones()

    def _init_drones(self):
        for i in range(self.num_drones):
            drone_id = f"drone_{i}"
            self.drones[drone_id] = EnergyManagementSystem()

    def optimize_power_allocation(self, total_required: float) -> Dict:
        available_total = 0
        for ems in self.drones.values():
            available_total += ems.solar_panel.power

        if available_total >= total_required:
            allocation = "self_sufficient"
            grid_power = 0
        else:
            allocation = "grid_assisted"
            grid_power = total_required - available_total

        return {
            "total_required_w": total_required,
            "available_w": available_total,
            "grid_power_w": grid_power,
            "strategy": allocation,
            "efficiency": available_total / total_required
            if total_required > 0
            else 1.0,
        }


def run_energy_harvesting_simulation():
    ems = EnergyManagementSystem()
    results = ems.simulate_operation(duration_h=12)
    return results


if __name__ == "__main__":
    print(run_energy_harvesting_simulation())
