<?php
/**
 * Fleet Web Portal — PHP stub for Phase 614
 * Web-based fleet management portal for drone swarm operations.
 */

declare(strict_types=1);

// ===== Configuration =====

define('APP_VERSION', '1.0.0');
define('MAX_DRONES', 50);
define('REFRESH_INTERVAL', 5);  // seconds
define('API_BASE_URL', 'http://localhost:8080/api/v1');

// ===== Data Models =====

class DroneRecord {
    public string $droneId;
    public string $status;
    public float $battery;
    public float $altitude;
    public float $latitude;
    public float $longitude;
    public float $speed;
    public string $lastSeen;
    public string $missionId;

    public function __construct(array $data) {
        $this->droneId   = $data['drone_id']  ?? 'UNKNOWN';
        $this->status    = $data['status']     ?? 'offline';
        $this->battery   = (float)($data['battery']   ?? 0.0);
        $this->altitude  = (float)($data['altitude']  ?? 0.0);
        $this->latitude  = (float)($data['latitude']  ?? 0.0);
        $this->longitude = (float)($data['longitude'] ?? 0.0);
        $this->speed     = (float)($data['speed']     ?? 0.0);
        $this->lastSeen  = $data['last_seen']  ?? date('Y-m-d H:i:s');
        $this->missionId = $data['mission_id'] ?? '';
    }

    public function isHealthy(): bool {
        return $this->battery > 20.0 && $this->status !== 'error';
    }

    public function getBatteryClass(): string {
        if ($this->battery > 50) return 'battery-good';
        if ($this->battery > 20) return 'battery-warning';
        return 'battery-critical';
    }

    public function toArray(): array {
        return [
            'drone_id'   => $this->droneId,
            'status'     => $this->status,
            'battery'    => $this->battery,
            'altitude'   => $this->altitude,
            'latitude'   => $this->latitude,
            'longitude'  => $this->longitude,
            'speed'      => $this->speed,
            'last_seen'  => $this->lastSeen,
            'mission_id' => $this->missionId,
            'healthy'    => $this->isHealthy(),
        ];
    }
}

class MissionRecord {
    public string $missionId;
    public string $name;
    public string $status;
    public float $progress;
    public array $droneIds;
    public ?string $startTime;

    public function __construct(array $data) {
        $this->missionId = $data['mission_id'] ?? '';
        $this->name      = $data['name']       ?? 'Unnamed';
        $this->status    = $data['status']     ?? 'pending';
        $this->progress  = (float)($data['progress'] ?? 0.0);
        $this->droneIds  = $data['drone_ids']  ?? [];
        $this->startTime = $data['start_time'] ?? null;
    }

    public function getProgressPercent(): int {
        return (int)round($this->progress * 100);
    }
}

// ===== API Client =====

class FleetApiClient {
    private string $baseUrl;
    private int $timeout;

    public function __construct(string $baseUrl = API_BASE_URL, int $timeout = 5) {
        $this->baseUrl = rtrim($baseUrl, '/');
        $this->timeout = $timeout;
    }

    /**
     * Fetch fleet status from GCS API.
     * Returns stub data for portal demonstration.
     */
    public function getFleet(): array {
        // Stub: generate simulated fleet data
        $drones = [];
        for ($i = 1; $i <= 5; $i++) {
            $drones[] = new DroneRecord([
                'drone_id'   => sprintf('D%03d', $i),
                'status'     => $i === 3 ? 'error' : 'active',
                'battery'    => 100.0 - ($i * 12.5),
                'altitude'   => 50.0 + ($i * 5),
                'latitude'   => 37.5665 + ($i * 0.001),
                'longitude'  => 126.9780 + ($i * 0.001),
                'speed'      => 5.0 + $i,
                'mission_id' => $i <= 3 ? 'M001' : '',
            ]);
        }
        return $drones;
    }

    public function getMissions(): array {
        return [
            new MissionRecord([
                'mission_id' => 'M001',
                'name'       => 'Patrol Alpha',
                'status'     => 'active',
                'progress'   => 0.65,
                'drone_ids'  => ['D001', 'D002', 'D003'],
                'start_time' => date('Y-m-d H:i:s', time() - 3600),
            ]),
            new MissionRecord([
                'mission_id' => 'M002',
                'name'       => 'Survey Beta',
                'status'     => 'pending',
                'progress'   => 0.0,
                'drone_ids'  => ['D004', 'D005'],
            ]),
        ];
    }

    public function sendCommand(string $droneId, string $command, array $params = []): array {
        // Stub: would POST to /api/v1/commands
        return [
            'success'    => true,
            'command_id' => uniqid('CMD-'),
            'drone_id'   => $droneId,
            'command'    => $command,
            'accepted'   => true,
        ];
    }
}

// ===== Fleet Dashboard =====

class FleetDashboard {
    private FleetApiClient $client;
    private array $drones = [];
    private array $missions = [];

    public function __construct(FleetApiClient $client) {
        $this->client = $client;
    }

    public function refresh(): void {
        $this->drones   = $this->client->getFleet();
        $this->missions = $this->client->getMissions();
    }

    public function getFleetStats(): array {
        $total   = count($this->drones);
        $active  = count(array_filter($this->drones, fn($d) => $d->status === 'active'));
        $errors  = count(array_filter($this->drones, fn($d) => $d->status === 'error'));
        $avgBat  = $total > 0
            ? array_sum(array_map(fn($d) => $d->battery, $this->drones)) / $total
            : 0.0;

        return [
            'total'        => $total,
            'active'       => $active,
            'errors'       => $errors,
            'avg_battery'  => round($avgBat, 1),
            'missions'     => count($this->missions),
            'phase'        => '614',
        ];
    }

    public function renderTextSummary(): string {
        $stats = $this->getFleetStats();
        $lines = ["=== Fleet Web Portal Dashboard ==="];
        $lines[] = "Phase 614 | Fleet Web Portal v" . APP_VERSION;
        $lines[] = sprintf("Drones: %d total | %d active | %d errors", $stats['total'], $stats['active'], $stats['errors']);
        $lines[] = sprintf("Avg battery: %.1f%% | Active missions: %d", $stats['avg_battery'], $stats['missions']);
        foreach ($this->drones as $drone) {
            $lines[] = sprintf("  %s [%s] bat=%.0f%% alt=%.1fm", $drone->droneId, $drone->status, $drone->battery, $drone->altitude);
        }
        return implode("\n", $lines);
    }
}

// ===== Main =====

$client    = new FleetApiClient();
$dashboard = new FleetDashboard($client);
$dashboard->refresh();

echo $dashboard->renderTextSummary() . PHP_EOL;
echo "Portal loaded successfully." . PHP_EOL;
