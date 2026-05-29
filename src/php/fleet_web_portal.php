<?php
// Phase 614: Fleet Web Portal — PHP Backend
// 함대 관리 웹 포털 백엔드

declare(strict_types=1);

class DroneRecord {
    public string $droneId;
    public float $lat;
    public float $lon;
    public float $alt;
    public float $battery;
    public string $status;
    public int $lastSeen;

    public function __construct(string $id, float $lat, float $lon, float $alt, float $battery, string $status) {
        $this->droneId = $id;
        $this->lat = $lat;
        $this->lon = $lon;
        $this->alt = $alt;
        $this->battery = $battery;
        $this->status = $status;
        $this->lastSeen = time();
    }

    public function isActive(): bool {
        return $this->status !== 'idle' && (time() - $this->lastSeen) < 30;
    }

    public function toArray(): array {
        return [
            'drone_id' => $this->droneId,
            'position' => ['lat' => $this->lat, 'lon' => $this->lon, 'alt' => $this->alt],
            'battery' => $this->battery,
            'status' => $this->status,
            'last_seen' => $this->lastSeen,
        ];
    }
}

class FleetManager {
    /** @var DroneRecord[] */
    private array $fleet = [];
    /** @var array<string, string[]> */
    private array $missions = [];
    private int $alertCount = 0;

    public function registerDrone(DroneRecord $drone): void {
        $this->fleet[$drone->droneId] = $drone;
    }

    public function updatePosition(string $droneId, float $lat, float $lon, float $alt): bool {
        if (!isset($this->fleet[$droneId])) {
            return false;
        }
        $this->fleet[$droneId]->lat = $lat;
        $this->fleet[$droneId]->lon = $lon;
        $this->fleet[$droneId]->alt = $alt;
        $this->fleet[$droneId]->lastSeen = time();
        return true;
    }

    public function getFleetStatus(): array {
        $total = count($this->fleet);
        $active = 0;
        $lowBattery = 0;
        foreach ($this->fleet as $drone) {
            if ($drone->isActive()) $active++;
            if ($drone->battery < 0.2) $lowBattery++;
        }
        return [
            'total_drones' => $total,
            'active' => $active,
            'idle' => $total - $active,
            'low_battery' => $lowBattery,
            'alert_count' => $this->alertCount,
        ];
    }

    public function assignMission(string $missionId, array $droneIds): bool {
        foreach ($droneIds as $id) {
            if (!isset($this->fleet[$id])) return false;
        }
        $this->missions[$missionId] = $droneIds;
        foreach ($droneIds as $id) {
            $this->fleet[$id]->status = 'mission';
        }
        return true;
    }

    public function getMissions(): array {
        return $this->missions;
    }

    public function getDronesJSON(): string {
        $data = array_map(fn(DroneRecord $d) => $d->toArray(), $this->fleet);
        return json_encode(array_values($data), JSON_PRETTY_PRINT);
    }

    public function checkAlerts(): array {
        $alerts = [];
        foreach ($this->fleet as $drone) {
            if ($drone->battery < 0.1) {
                $alerts[] = ['type' => 'critical_battery', 'drone' => $drone->droneId, 'battery' => $drone->battery];
                $this->alertCount++;
            }
            if (!$drone->isActive() && $drone->status === 'flying') {
                $alerts[] = ['type' => 'connection_lost', 'drone' => $drone->droneId];
                $this->alertCount++;
            }
        }
        return $alerts;
    }
}
