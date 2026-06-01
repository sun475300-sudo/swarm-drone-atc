<?php
// Phase 614 — PHP Fleet Web Portal for SDACS
// Web dashboard for fleet management and mission control

declare(strict_types=1);

namespace SDACS\Fleet;

final class DroneState
{
    public function __construct(
        public readonly string $id,
        public readonly float $x,
        public readonly float $y,
        public readonly float $z,
        public readonly float $batteryPct,
        public readonly string $flightPhase,
    ) {}

    public static function fromArray(array $data): self
    {
        return new self(
            $data['id'],
            (float) $data['x'],
            (float) $data['y'],
            (float) $data['z'],
            (float) $data['battery_pct'],
            $data['flight_phase'],
        );
    }
}

final class FleetWebPortal
{
    private string $apiBase;

    public function __construct(string $apiBase = 'http://localhost:8000')
    {
        $this->apiBase = rtrim($apiBase, '/');
    }

    public function getDrones(): array
    {
        $json = $this->get('/api/drones');
        return array_map([DroneState::class, 'fromArray'], $json);
    }

    public function getMetrics(): array
    {
        return $this->get('/api/metrics');
    }

    public function runScenario(string $scenario, int $duration): array
    {
        return $this->post('/api/scenario', ['scenario' => $scenario, 'duration' => $duration]);
    }

    private function get(string $path): array
    {
        $url = $this->apiBase . $path;
        $ctx = stream_context_create(['http' => ['method' => 'GET', 'header' => 'Accept: application/json']]);
        $body = @file_get_contents($url, false, $ctx);
        return $body !== false ? json_decode($body, true) : [];
    }

    private function post(string $path, array $payload): array
    {
        $url = $this->apiBase . $path;
        $ctx = stream_context_create(['http' => [
            'method' => 'POST',
            'header' => "Content-Type: application/json\r\nAccept: application/json",
            'content' => json_encode($payload),
        ]]);
        $body = @file_get_contents($url, false, $ctx);
        return $body !== false ? json_decode($body, true) : [];
    }
}
