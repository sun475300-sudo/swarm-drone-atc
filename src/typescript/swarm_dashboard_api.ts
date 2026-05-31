// Swarm Dashboard API — SDACS Phase 611
export interface DroneStatus {
  id: string;
  lat: number;
  lon: number;
  alt: number;
  battery: number;
}

export async function fetchDrones(): Promise<DroneStatus[]> {
  const response = await fetch('/api/v1/drones');
  return response.json();
}

export function formatDrone(d: DroneStatus): string {
  return `[${d.id}] ${d.lat.toFixed(4)},${d.lon.toFixed(4)} alt=${d.alt}m`;
}
