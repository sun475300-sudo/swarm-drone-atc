/**
 * swarm_dashboard_api.ts
 * TypeScript REST API stub for the swarm drone dashboard.
 * Exposes endpoints for drone telemetry, conflict alerts, and airspace status.
 */

import express, { Request, Response } from "express";

const app = express();
app.use(express.json());

const PORT = process.env.PORT ?? 3000;

interface DroneStatus {
  droneId: string;
  position: { x: number; y: number; z: number };
  velocity: number;
  batteryPct: number;
  state: "idle" | "flying" | "returning" | "emergency";
}

// GET /api/drones — list all active drones
app.get("/api/drones", (_req: Request, res: Response) => {
  // TODO: fetch from SwarmSimulator state store
  const drones: DroneStatus[] = [];
  res.json({ success: true, data: drones });
});

// GET /api/drones/:id — single drone telemetry
app.get("/api/drones/:id", (req: Request, res: Response) => {
  const { id } = req.params;
  // TODO: look up drone by id
  res.json({ success: true, data: { droneId: id } });
});

// GET /api/alerts — active conflict/collision alerts
app.get("/api/alerts", (_req: Request, res: Response) => {
  // TODO: pull from AirspaceController conflict queue
  res.json({ success: true, data: [] });
});

// GET /api/status — overall airspace health
app.get("/api/status", (_req: Request, res: Response) => {
  res.json({
    success: true,
    data: {
      activeDrones: 0,
      conflicts: 0,
      collisionResolutionRate: 1.0,
      simulationTime: 0,
    },
  });
});

app.listen(PORT, () => {
  console.log(`Swarm Dashboard API listening on port ${PORT}`);
});

export default app;
