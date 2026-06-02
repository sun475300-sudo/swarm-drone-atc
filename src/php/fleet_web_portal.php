<?php
// Phase 614: Fleet Web Portal — PHP
// SDACS web portal for drone fleet management

declare(strict_types=1);

namespace SDACS\Portal;

class DroneRecord {
    public function __construct(
        public readonly string $droneId,
        public readonly float  $lat,
        public readonly float  $lon,
        public readonly float  $alt,
        public readonly float  $battery,
        public readonly string $status = 'idle'
    ) {}

    public function toArray(): array {
        return [
            'drone_id' => $this->droneId,
            'lat'      => $this->lat,
            'lon'      => $this->lon,
            'alt'      => $this->alt,
            'battery'  => $this->battery,
            'status'   => $this->status,
        ];
    }
}

class FleetPortal {
    private array $drones = [];

    public function register(DroneRecord $drone): void {
        $this->drones[$drone->droneId] = $drone;
    }

    public function getAll(): array {
        return array_values(array_map(fn($d) => $d->toArray(), $this->drones));
    }

    public function get(string $droneId): ?DroneRecord {
        return $this->drones[$droneId] ?? null;
    }

    public function count(): int {
        return count($this->drones);
    }
}

$portal = new FleetPortal();
$portal->register(new DroneRecord('D001', 37.5665, 126.978, 60.0, 85.0, 'active'));
echo json_encode(['fleet' => $portal->getAll()]);
