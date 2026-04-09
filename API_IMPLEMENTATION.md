# SDACS API 2.1.0 - Complete Implementation Guide

## File Location
`/sessions/sweet-magical-bell/mnt/swarm-drone-atc/api/server.py`

## Quick Start

### Run the API Server
```bash
cd /sessions/sweet-magical-bell/mnt/swarm-drone-atc
python -m api.server
# or
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

### Access Interactive Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## REST API Endpoints (19 total)

### Simulation Management

#### Start Simulation
```
POST /api/simulation/start
Content-Type: application/json

{
  "duration": 60,           # 1-3600 seconds
  "num_drones": 50,         # 1-2000 drones
  "scenario": "default",    # or: high_density, comms_loss, etc.
  "seed": 42                # optional, for reproducibility
}

Response:
{
  "simulation_id": "sim_a1b2c3d4",
  "status": "running",
  "config": {...},
  "started_at_s": 1712592000.123
}
```

#### List Simulations
```
GET /api/simulation

Response:
{
  "simulations": [
    {
      "simulation_id": "sim_a1b2c3d4",
      "status": "running",
      "started_at_s": 1712592000.123,
      "elapsed_s": 15.3,
      "sim_time_s": 12.5
    }
  ],
  "total": 1
}
```

#### Get Simulation Status
```
GET /api/simulation/{simulation_id}/status

Response:
{
  "simulation_id": "sim_a1b2c3d4",
  "status": "running",
  "config": {...},
  "started_at_s": 1712592000.123,
  "elapsed_s": 15.3,
  "sim_time_s": 12.5,
  "drones_active": 48,
  "error": null,
  "result_summary": null
}
```

#### Stop Simulation
```
POST /api/simulation/{simulation_id}/stop

Response:
{
  "simulation_id": "sim_a1b2c3d4",
  "status": "stopping",
  "message": "Stop signal sent"
}
```

### Drone Data

#### Get All Drones
```
GET /api/drones?simulation_id=sim_a1b2c3d4&phase=ENROUTE&limit=100

Query Parameters:
  - simulation_id (required): Simulation ID
  - phase (optional): Filter by flight phase (TAKEOFF, ENROUTE, LANDING, etc.)
  - limit (optional): Max results (default: 100, max: 2000)

Response:
{
  "simulation_id": "sim_a1b2c3d4",
  "count": 48,
  "timestamp_s": 1712592000.123,
  "drones": [
    {
      "drone_id": "drone_0",
      "x": 100.5,
      "y": 200.3,
      "z": 60.0,
      "vx": 15.2,
      "vy": -8.1,
      "vz": 0.0,
      "velocity_magnitude": 17.3,
      "battery_pct": 85.5,
      "flight_phase": "ENROUTE",
      "distance_flown_m": 5420.0,
      "timestamp_s": 1712592000.123
    }
  ]
}
```

#### Get Single Drone
```
GET /api/drones/{drone_id}?simulation_id=sim_a1b2c3d4

Response:
{
  "drone_id": "drone_5",
  "x": 150.2,
  "y": 250.8,
  "z": 60.0,
  "vx": 12.5,
  "vy": 8.3,
  "vz": 0.0,
  "velocity_magnitude": 15.0,
  "battery_pct": 82.3,
  "flight_phase": "ENROUTE",
  "distance_flown_m": 4850.0,
  "timestamp_s": 1712592000.123
}
```

### Conflicts

#### Get Conflicts
```
GET /api/conflicts?simulation_id=sim_a1b2c3d4&severity=high

Query Parameters:
  - simulation_id (required): Simulation ID
  - severity (optional): low|medium|high

Response:
{
  "simulation_id": "sim_a1b2c3d4",
  "active_count": 3,
  "timestamp_s": 1712592000.123,
  "conflicts": [
    {
      "conflict_id": "conf_12.5_drone_5",
      "drone_ids": ["drone_5", "drone_12"],
      "severity": "medium",
      "distance_m": 85.3,
      "timestamp_s": 12.5
    }
  ]
}
```

### Metrics

#### Get Metrics
```
GET /api/metrics?simulation_id=sim_a1b2c3d4

Response:
{
  "simulation_id": "sim_a1b2c3d4",
  "timestamp_s": 1712592000.123,
  "collision_count": 0,
  "near_miss_count": 2,
  "conflicts_total": 15,
  "conflict_resolution_rate_pct": 98.5,
  "advisories_issued": 23,
  "clearances_approved": 145,
  "clearances_denied": 3,
  "comm_drop_rate": 0.02,
  "total_distance_km": 125.4,
  "energy_efficiency_wh_per_km": 3.2,
  "advisory_latency_p50": 0.15,
  "advisory_latency_p99": 0.45
}
```

### Configuration

#### Get Current Config
```
GET /api/config

Response:
{
  "drones_default_count": 50,
  "bounds_m": 1000.0,
  "dt_s": 0.1,
  "bounds_vertical_m": 120.0,
  "conflict_detection_threshold_m": 100.0
}
```

### Scenarios

#### List Available Scenarios
```
GET /api/scenarios

Response:
{
  "scenarios": [
    {
      "name": "adversarial_intrusion",
      "description": null,
      "default_drones": 50
    },
    {
      "name": "comms_loss",
      "description": null,
      "default_drones": 30
    }
  ],
  "total": 7
}
```

#### Run Scenario
```
POST /api/scenario/high_density?duration=120&seed=42

Query Parameters:
  - duration (optional): 1-3600 seconds
  - seed (optional): Random seed

Response:
{
  "simulation_id": "sim_xyz789",
  "status": "running",
  "config": {...},
  "started_at_s": 1712592000.123
}
```

### Airspace

#### Get Zones
```
GET /api/zones

Response:
{
  "zones": [
    {"id": "zone_1", "bounds": {...}, "type": "controlled"}
  ]
}
```

### Health Check

```
GET /health

Response:
{
  "status": "healthy",
  "timestamp_s": 1712592000.123,
  "version": "2.1.0",
  "active_simulations": 2
}
```

---

## WebSocket Endpoints (3 total)

### 1. Telemetry Stream
**URL**: `ws://localhost:8000/ws/telemetry/{simulation_id}`

**Frequency**: 1 Hz (1 message per second)

**Message Format**:
```json
{
  "type": "telemetry",
  "simulation_id": "sim_a1b2c3d4",
  "timestamp_s": 1712592000.123,
  "drones_count": 48,
  "drones": [
    {
      "drone_id": "drone_0",
      "x": 100.5,
      "y": 200.3,
      "z": 60.0,
      "vx": 15.2,
      "vy": -8.1,
      "vz": 0.0,
      "velocity_magnitude": 17.3,
      "battery_pct": 85.5,
      "flight_phase": "ENROUTE",
      "distance_flown_m": 5420.0,
      "timestamp_s": 1712592000.123
    }
  ]
}
```

**Data Fields**:
- Position (x, y, z) in meters
- Velocity vector (vx, vy, vz) in m/s
- Velocity magnitude in m/s
- Battery percentage (0-100)
- Flight phase enum
- Total distance flown in meters
- Server timestamp in seconds since epoch

**Use Cases**:
- Real-time visualization dashboards
- 3D drone tracking
- Flight monitoring
- Live control room displays

**JavaScript Client Example**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/telemetry/sim_a1b2c3d4');

ws.onopen = () => console.log('Connected to telemetry stream');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`${data.drones_count} drones at t=${data.timestamp_s}`);
  
  data.drones.forEach(drone => {
    updateDronePosition(drone.drone_id, {
      x: drone.x,
      y: drone.y,
      z: drone.z,
      battery: drone.battery_pct
    });
  });
};

ws.onerror = (error) => console.error('WebSocket error:', error);
ws.onclose = () => console.log('Disconnected from telemetry stream');
```

---

### 2. Event Stream
**URL**: `ws://localhost:8000/ws/events/{simulation_id}`

**Frequency**: Real-time (as events occur, ~10 Hz polling)

**Message Format**:
```json
{
  "type": "event",
  "simulation_id": "sim_a1b2c3d4",
  "timestamp_s": 1712592000.123,
  "event_type": "CONFLICT",
  "event_data": {
    "type": "CONFLICT",
    "t": 12.5,
    "drone_id": "drone_5",
    "distance_m": 85.3
  }
}
```

**Event Types**:
- `CONFLICT` - Potential conflict detected
- `NEAR_MISS` - Close approach detected
- `COLLISION` - Collision occurred
- `ADVISORY_ISSUED` - Resolution advisory issued
- `CLEARANCE_APPROVED` - Waypoint clearance approved
- `CLEARANCE_DENIED` - Clearance request denied
- `ENROUTE_NO_GOAL_LANDING` - Drone transitioning to landing
- (Plus any other SimulationAnalytics events)

**Use Cases**:
- Real-time alerts and notifications
- Safety monitoring systems
- Event logging and analysis
- Autonomous response triggers

**Python Client Example**:
```python
import asyncio
import websockets
import json

async def listen_events(sim_id):
    uri = f"ws://localhost:8000/ws/events/{sim_id}"
    async with websockets.connect(uri) as ws:
        while True:
            msg = await ws.recv()
            event = json.loads(msg)
            
            if event['event_type'] == 'COLLISION':
                print(f"COLLISION ALERT: {event['event_data']}")
                trigger_emergency_response()
            
            elif event['event_type'] == 'CONFLICT':
                print(f"Conflict detected: {event['event_data']}")

asyncio.run(listen_events("sim_a1b2c3d4"))
```

---

### 3. Metrics Stream
**URL**: `ws://localhost:8000/ws/metrics/{simulation_id}`

**Frequency**: Every 5 seconds

**Message Format**:
```json
{
  "type": "metrics",
  "simulation_id": "sim_a1b2c3d4",
  "timestamp_s": 1712592000.123,
  "metrics": {
    "simulation_id": "sim_a1b2c3d4",
    "timestamp_s": 1712592000.123,
    "collision_count": 0,
    "near_miss_count": 2,
    "conflicts_total": 15,
    "conflict_resolution_rate_pct": 98.5,
    "advisories_issued": 23,
    "clearances_approved": 145,
    "clearances_denied": 3,
    "comm_drop_rate": 0.02,
    "total_distance_km": 125.4,
    "energy_efficiency_wh_per_km": 3.2,
    "advisory_latency_p50": 0.15,
    "advisory_latency_p99": 0.45
  }
}
```

**Metrics Provided**:
- Safety: collisions, near misses, conflicts
- Resolution: advisory issuance, clearance approvals
- Efficiency: distance, energy consumption
- Communications: drop rate
- Performance: latency percentiles

**Use Cases**:
- KPI dashboards
- Performance monitoring
- System health tracking
- Real-time analytics

**React Client Example**:
```jsx
import { useEffect, useState } from 'react';

function MetricsDisplay({ simulationId }) {
  const [metrics, setMetrics] = useState(null);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/metrics/${simulationId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMetrics(data.metrics);
    };
    
    return () => ws.close();
  }, [simulationId]);
  
  if (!metrics) return <div>Loading metrics...</div>;
  
  return (
    <div className="metrics-dashboard">
      <div className="metric">
        <h3>Collisions</h3>
        <p className="value">{metrics.collision_count}</p>
      </div>
      <div className="metric">
        <h3>Resolution Rate</h3>
        <p className="value">{metrics.conflict_resolution_rate_pct.toFixed(1)}%</p>
      </div>
      <div className="metric">
        <h3>Total Distance</h3>
        <p className="value">{metrics.total_distance_km.toFixed(1)} km</p>
      </div>
    </div>
  );
}
```

---

## Thread Safety & Concurrency

### Design
- **REST handlers**: Use `threading.RLock()` for simulation state access
- **WebSocket streams**: Use `asyncio.Lock()` for client list modifications
- **Simulator thread**: Background thread runs simulation independently
- **Concurrent broadcasts**: Multiple WebSocket clients per simulation supported

### Safety Guarantees
- No race conditions on simulation state reads
- Graceful handling of disconnects
- Automatic cleanup of failed connections
- Thread-safe drone state extraction

---

## Error Handling

### HTTP Status Codes
- `200 OK` - Successful GET/POST
- `404 Not Found` - Simulation or drone doesn't exist
- `409 Conflict` - Metrics not available (simulation still running)
- `500 Internal Server Error` - Initialization or processing failure

### WebSocket Errors
- Connection drops handled gracefully
- Automatic client removal on send failure
- Detailed error logging for debugging

### Example Error Response
```json
{
  "detail": "Simulation sim_invalid not found"
}
```

---

## Code Architecture

### Core Components

**ConnectionManager Class**
- Manages WebSocket client connections per simulation
- Separate pools for telemetry, events, metrics
- Thread-safe broadcast methods
- Automatic client cleanup

**Pydantic Models** (17 total)
- Type-safe request/response validation
- Automatic JSON serialization
- Field-level validation and documentation

**Helper Functions**
- `_extract_drones()` - Extract drone states with velocities
- `_extract_conflicts()` - Convert events to conflict objects
- `_build_metrics_from_result()` - Create metrics response
- `_get_available_scenarios()` - Scan scenario directory

---

## Deployment Recommendations

### Development
```bash
python -m api.server
# or with auto-reload
uvicorn api.server:app --reload
```

### Production
```bash
# Using gunicorn with uvicorn workers
gunicorn api.server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Security Checklist
- [ ] Configure CORS origins (not "*" in production)
- [ ] Add authentication middleware
- [ ] Implement rate limiting
- [ ] Use HTTPS/WSS in production
- [ ] Add API key validation
- [ ] Configure logging to persistent storage
- [ ] Monitor memory usage (WebSocket clients)
- [ ] Set connection timeouts

### Monitoring
- Track active WebSocket connections per simulation
- Monitor CPU/memory usage of background simulator threads
- Log all errors with timestamps
- Alert on simulation failures

---

## Testing

### Unit Tests
```python
def test_get_simulation_status():
    # Test simulation status endpoint
    pass

def test_drone_extraction():
    # Test drone state extraction
    pass
```

### Integration Tests
```python
async def test_websocket_telemetry():
    # Test telemetry stream
    pass

async def test_concurrent_clients():
    # Test multiple WebSocket clients
    pass
```

### Load Testing
```bash
# Load test with Apache Bench
ab -n 1000 -c 10 http://localhost:8000/health

# WebSocket load test
python -m pytest tests/load_test_websockets.py
```

---

## Version History

**2.1.0** (Latest)
- Added 8 new REST endpoints
- Added 3 WebSocket streams
- Implemented ConnectionManager
- Added 17 Pydantic models
- Full type annotations
- CORS support
- Thread-safe concurrent access

**2.0.0** (Previous)
- Basic simulation lifecycle
- Drone query endpoints
- Metrics retrieval

---

## Support & Documentation

- **OpenAPI Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Source**: `/sessions/sweet-magical-bell/mnt/swarm-drone-atc/api/server.py`
