<?php
/**
 * SDACS Fleet Web Portal — PHP (Phase 614)
 * 드론 군집 웹 포털 백엔드
 */

declare(strict_types=1);

namespace SDACS\Portal;

/**
 * 드론 데이터 모델
 */
class DroneModel
{
    public string $id;
    public float $x;
    public float $y;
    public float $z;
    public float $battery;
    public string $state;
    public int $timestamp;

    public function __construct(string $id, float $x, float $y, float $z, float $battery, string $state = 'FLYING')
    {
        $this->id = $id;
        $this->x = $x;
        $this->y = $y;
        $this->z = $z;
        $this->battery = $battery;
        $this->state = $state;
        $this->timestamp = time();
    }

    public function isLowBattery(): bool
    {
        return $this->battery < 20.0;
    }

    public function toArray(): array
    {
        return [
            'id'        => $this->id,
            'x'         => $this->x,
            'y'         => $this->y,
            'z'         => $this->z,
            'battery'   => $this->battery,
            'state'     => $this->state,
            'timestamp' => $this->timestamp,
        ];
    }
}

/**
 * Fleet 관리자 (Phase 614)
 */
class FleetManager
{
    private array $fleet = [];
    private array $conflicts = [];
    private float $separationThreshold;

    public function __construct(float $threshold = 50.0)
    {
        $this->separationThreshold = $threshold;
    }

    public function registerDrone(DroneModel $drone): void
    {
        $this->fleet[$drone->id] = $drone;
    }

    public function updateDrone(string $id, array $updates): bool
    {
        if (!isset($this->fleet[$id])) {
            return false;
        }
        foreach ($updates as $key => $value) {
            if (property_exists($this->fleet[$id], $key)) {
                $this->fleet[$id]->$key = $value;
            }
        }
        return true;
    }

    public function detectConflicts(): array
    {
        $drones = array_values($this->fleet);
        $conflicts = [];
        for ($i = 0; $i < count($drones); $i++) {
            for ($j = $i + 1; $j < count($drones); $j++) {
                $a = $drones[$i];
                $b = $drones[$j];
                $dist = sqrt(($a->x - $b->x) ** 2 + ($a->y - $b->y) ** 2 + ($a->z - $b->z) ** 2);
                if ($dist < $this->separationThreshold) {
                    $conflicts[] = ['droneA' => $a->id, 'droneB' => $b->id, 'distance' => $dist];
                }
            }
        }
        $this->conflicts = $conflicts;
        return $conflicts;
    }

    public function getStats(): array
    {
        $drones = array_values($this->fleet);
        $n = count($drones);
        if ($n === 0) {
            return ['total' => 0, 'active' => 0, 'low_battery' => 0, 'avg_battery' => 0.0];
        }
        $active = count(array_filter($drones, fn($d) => in_array($d->state, ['FLYING', 'HOVERING'])));
        $lowBat = count(array_filter($drones, fn($d) => $d->isLowBattery()));
        $avgBat = array_sum(array_map(fn($d) => $d->battery, $drones)) / $n;
        return ['total' => $n, 'active' => $active, 'low_battery' => $lowBat, 'avg_battery' => round($avgBat, 2)];
    }

    public function getDrone(string $id): ?DroneModel
    {
        return $this->fleet[$id] ?? null;
    }

    public function getAllDrones(): array
    {
        return array_map(fn($d) => $d->toArray(), $this->fleet);
    }

    public function droneCount(): int
    {
        return count($this->fleet);
    }
}

/**
 * 간단한 REST 라우터
 */
class Router
{
    private array $routes = [];

    public function get(string $path, callable $handler): void
    {
        $this->routes['GET'][$path] = $handler;
    }

    public function post(string $path, callable $handler): void
    {
        $this->routes['POST'][$path] = $handler;
    }

    public function dispatch(string $method, string $path): array
    {
        $handler = $this->routes[$method][$path] ?? null;
        if ($handler === null) {
            return ['status' => 404, 'body' => ['error' => 'Not found']];
        }
        return ['status' => 200, 'body' => $handler()];
    }

    public function routeCount(): int
    {
        return array_sum(array_map('count', $this->routes));
    }
}
