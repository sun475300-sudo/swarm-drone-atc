<?php
// Fleet Web Portal — SDACS Phase 614
namespace SDACS;

class DroneStatus {
    public string $id;
    public float $lat;
    public float $lon;
    public float $alt;
    public int $battery;
    
    public function __construct(string $id, float $lat, float $lon, float $alt, int $battery) {
        $this->id = $id;
        $this->lat = $lat;
        $this->lon = $lon;
        $this->alt = $alt;
        $this->battery = $battery;
    }
}
