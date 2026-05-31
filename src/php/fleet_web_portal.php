<?php
/**
 * fleet_web_portal.php
 * PHP stub for the SDACS fleet management web portal.
 * Renders drone status table and proxies API calls to the dashboard API.
 */

declare(strict_types=1);

define('API_BASE', getenv('DASHBOARD_API') ?: 'http://localhost:3000/api');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Fetch JSON from the dashboard API.
 *
 * @param string $endpoint  e.g. "/drones"
 * @return array|null  Decoded JSON or null on error
 */
function api_get(string $endpoint): ?array {
    $url = API_BASE . $endpoint;
    $ctx = stream_context_create(['http' => ['timeout' => 5]]);
    $raw = @file_get_contents($url, false, $ctx);
    if ($raw === false) {
        return null;
    }
    $decoded = json_decode($raw, true);
    return $decoded['data'] ?? null;
}

// ---------------------------------------------------------------------------
// Controller
// ---------------------------------------------------------------------------

$drones = api_get('/drones') ?? [];
$alerts = api_get('/alerts') ?? [];
$status = api_get('/status') ?? [];

// ---------------------------------------------------------------------------
// View
// ---------------------------------------------------------------------------
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SDACS Fleet Portal</title>
</head>
<body>
<h1>SDACS Fleet Web Portal</h1>

<h2>Airspace Status</h2>
<ul>
    <li>Active drones: <?= htmlspecialchars((string)($status['activeDrones'] ?? 0)) ?></li>
    <li>Conflicts: <?= htmlspecialchars((string)($status['conflicts'] ?? 0)) ?></li>
    <li>Resolution rate: <?= htmlspecialchars((string)($status['collisionResolutionRate'] ?? 'n/a')) ?></li>
</ul>

<h2>Active Alerts (<?= count($alerts) ?>)</h2>
<?php if (empty($alerts)): ?>
    <p>No active alerts.</p>
<?php else: ?>
    <ul>
    <?php foreach ($alerts as $alert): ?>
        <li><?= htmlspecialchars(json_encode($alert)) ?></li>
    <?php endforeach; ?>
    </ul>
<?php endif; ?>

<h2>Drone Fleet (<?= count($drones) ?> drones)</h2>
<table border="1" cellpadding="4">
    <tr><th>ID</th><th>State</th><th>Battery %</th><th>Velocity m/s</th></tr>
    <?php foreach ($drones as $d): ?>
    <tr>
        <td><?= htmlspecialchars($d['droneId'] ?? '') ?></td>
        <td><?= htmlspecialchars($d['state'] ?? '') ?></td>
        <td><?= htmlspecialchars((string)($d['batteryPct'] ?? '')) ?></td>
        <td><?= htmlspecialchars((string)($d['velocity'] ?? '')) ?></td>
    </tr>
    <?php endforeach; ?>
</table>
</body>
</html>
