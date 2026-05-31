<?php
// fleet_web_portal.php - Web portal for SDACS fleet management
declare(strict_types=1);

namespace SDACS\Fleet;

class DroneState {
    public function __construct(
        public readonly string $id,
        public readonly float $latitude,
        public readonly float $longitude,
        public readonly float $altitude,
        public readonly int $battery,
        public readonly string $status
    ) {}
}

class FleetWebPortal {
    private string $apiBase;
    private array $drones = [];

    public function __construct(string $apiBase) {
        $this->apiBase = $apiBase;
    }

    public function fetchSnapshot(): array {
        $url = "{$this->apiBase}/api/v1/snapshot";
        $response = @file_get_contents($url);
        if ($response === false) return [];
        $data = json_decode($response, true);
        return $data ?? [];
    }

    public function renderDashboard(): string {
        $snapshot = $this->fetchSnapshot();
        $count = count($snapshot);
        return "<html><body><h1>SDACS Fleet Dashboard</h1><p>Drones: {$count}</p></body></html>";
    }
}
