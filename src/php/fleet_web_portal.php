<?php
// SDACS Phase 614 — PHP fleet management web portal
class FleetPortal {
    private string $apiUrl;
    public function __construct(string $apiUrl) { $this->apiUrl = $apiUrl; }
    public function getDrones(): array {
        $data = json_decode(file_get_contents($this->apiUrl . '/api/airspace/snapshot'), true);
        return $data['data']['drones'] ?? [];
    }
}
