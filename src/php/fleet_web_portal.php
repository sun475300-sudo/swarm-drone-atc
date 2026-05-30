<?php
/**
 * Phase 614: fleet_web_portal — PHP 기반 군집 드론 웹 포털
 * SDACS Fleet Management Web Portal
 */

declare(strict_types=1);

namespace SDACS\Web;

// 드론 상태 DTO
class DroneStatus
{
    public function __construct(
        public readonly int    $droneId,
        public readonly float  $lat,
        public readonly float  $lon,
        public readonly float  $alt,
        public readonly float  $battery,
        public readonly float  $speed,
        public readonly string $flightMode,
        public readonly bool   $isArmed,
        public readonly float  $timestamp,
    ) {}

    public static function fromArray(array $data): self
    {
        return new self(
            droneId:    (int)   ($data['drone_id'] ?? 0),
            lat:        (float) ($data['lat'] ?? 0.0),
            lon:        (float) ($data['lon'] ?? 0.0),
            alt:        (float) ($data['alt'] ?? 0.0),
            battery:    (float) ($data['battery'] ?? 100.0),
            speed:      (float) ($data['speed'] ?? 0.0),
            flightMode: (string)($data['flight_mode'] ?? 'STABILIZE'),
            isArmed:    (bool)  ($data['is_armed'] ?? false),
            timestamp:  (float) ($data['timestamp'] ?? microtime(true)),
        );
    }

    public function toArray(): array
    {
        return [
            'drone_id'    => $this->droneId,
            'lat'         => $this->lat,
            'lon'         => $this->lon,
            'alt'         => $this->alt,
            'battery'     => $this->battery,
            'speed'       => $this->speed,
            'flight_mode' => $this->flightMode,
            'is_armed'    => $this->isArmed,
            'timestamp'   => $this->timestamp,
        ];
    }
}

// API 응답 래퍼
class ApiResponse
{
    public static function success(mixed $data, ?array $meta = null): array
    {
        $resp = ['success' => true, 'data' => $data];
        if ($meta !== null) {
            $resp['meta'] = $meta;
        }
        return $resp;
    }

    public static function error(string $message, int $code = 400): array
    {
        return ['success' => false, 'error' => $message, 'code' => $code];
    }
}

// SDACS API 클라이언트 (cURL 기반)
class SDACSApiClient
{
    private string $baseUrl;
    private int    $timeout;

    public function __construct(string $baseUrl, int $timeout = 5)
    {
        $this->baseUrl = rtrim($baseUrl, '/');
        $this->timeout = $timeout;
    }

    public function getSnapshot(): array
    {
        return $this->get('/api/airspace/snapshot');
    }

    public function getDroneStatus(int $droneId): array
    {
        return $this->get("/api/drones/{$droneId}");
    }

    public function sendCommand(int $droneId, string $command, array $params = []): array
    {
        return $this->post("/api/drones/{$droneId}/command", [
            'command' => $command,
            'params'  => $params,
        ]);
    }

    public function runScenario(string $scenarioId): array
    {
        return $this->post("/api/scenarios/{$scenarioId}/run", []);
    }

    private function get(string $path): array
    {
        $ch = curl_init($this->baseUrl . $path);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => $this->timeout,
            CURLOPT_HTTPHEADER     => ['Accept: application/json'],
        ]);
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($body === false || $code !== 200) {
            return ApiResponse::error("HTTP {$code}", $code);
        }
        return json_decode($body, true) ?? ApiResponse::error('Invalid JSON');
    }

    private function post(string $path, array $payload): array
    {
        $json = json_encode($payload);
        $ch   = curl_init($this->baseUrl . $path);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => $json,
            CURLOPT_TIMEOUT        => $this->timeout,
            CURLOPT_HTTPHEADER     => [
                'Content-Type: application/json',
                'Accept: application/json',
            ],
        ]);
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($body === false) {
            return ApiResponse::error("Request failed", 500);
        }
        return json_decode($body, true) ?? ApiResponse::error('Invalid JSON');
    }
}

// 플리트 웹 포털 컨트롤러
class FleetPortalController
{
    private SDACSApiClient $api;

    public function __construct(SDACSApiClient $api)
    {
        $this->api = $api;
    }

    public function renderDashboard(): string
    {
        $snapshot = $this->api->getSnapshot();
        $drones   = $snapshot['data']['drones'] ?? [];
        $html = "<!DOCTYPE html>\n<html><head><title>SDACS Fleet Portal — Phase 614</title></head>\n<body>\n";
        $html .= "<h1>SDACS 군집 드론 포털</h1>\n";
        $html .= "<p>드론 수: " . count($drones) . "</p>\n";
        $html .= "<table border='1'>\n<tr><th>ID</th><th>고도</th><th>배터리</th><th>모드</th></tr>\n";
        foreach ($drones as $d) {
            $status = DroneStatus::fromArray($d);
            $color  = $status->battery >= 50 ? 'green' : ($status->battery >= 20 ? 'orange' : 'red');
            $html  .= "<tr><td>{$status->droneId}</td><td>{$status->alt}m</td>";
            $html  .= "<td style='color:{$color}'>{$status->battery}%</td><td>{$status->flightMode}</td></tr>\n";
        }
        $html .= "</table>\n</body></html>";
        return $html;
    }

    public function handleApiRequest(string $method, string $path, array $body = []): array
    {
        return match (true) {
            $method === 'GET' && $path === '/snapshot'          => $this->api->getSnapshot(),
            $method === 'POST' && str_starts_with($path, '/cmd') => $this->api->sendCommand(
                (int)($body['drone_id'] ?? 0),
                (string)($body['command'] ?? ''),
                (array)($body['params'] ?? [])
            ),
            default => ApiResponse::error('Not found', 404),
        };
    }
}

// Phase 614 진입점
echo "SDACS Fleet Web Portal — Phase 614\n";
$client     = new SDACSApiClient('http://localhost:8080');
$controller = new FleetPortalController($client);
echo "Fleet portal initialized\n";
echo "API base URL: http://localhost:8080\n";
