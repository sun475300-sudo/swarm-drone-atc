## Phase 308: Nim Digital Twin State Manager
## Memory-efficient digital twin synchronization with Nim's
## deterministic memory management and zero-overhead abstractions.

import std/[tables, math, times, sequtils, strformat, algorithm]

type
  Vec3* = object
    x*, y*, z*: float64

  TwinStatus* = enum
    Synced, Lagging, Predicted, Disconnected

  TwinState* = object
    twinId*: string
    physicalPos*: Vec3
    digitalPos*: Vec3
    physicalVel*: Vec3
    syncTimestamp*: float64
    status*: TwinStatus
    divergence*: float64
    lagMs*: float64

  SyncEvent* = object
    eventId*: string
    twinId*: string
    eventType*: string
    timestamp*: float64

  DigitalTwinManager* = object
    twins*: Table[string, TwinState]
    events*: seq[SyncEvent]
    syncCount*: int
    maxLagMs*: float64
    maxDivergenceM*: float64
    eventCounter*: int

# ── Vec3 Operations ──────────────────────────────────────────────
proc `+`*(a, b: Vec3): Vec3 =
  Vec3(x: a.x + b.x, y: a.y + b.y, z: a.z + b.z)

proc `-`*(a, b: Vec3): Vec3 =
  Vec3(x: a.x - b.x, y: a.y - b.y, z: a.z - b.z)

proc `*`*(a: Vec3, s: float64): Vec3 =
  Vec3(x: a.x * s, y: a.y * s, z: a.z * s)

proc length*(v: Vec3): float64 =
  sqrt(v.x * v.x + v.y * v.y + v.z * v.z)

proc distance*(a, b: Vec3): float64 =
  (a - b).length()

# ── Digital Twin Manager ─────────────────────────────────────────
proc newDigitalTwinManager*(maxLagMs: float64 = 500.0,
                            maxDivM: float64 = 5.0): DigitalTwinManager =
  DigitalTwinManager(
    twins: initTable[string, TwinState](),
    events: @[],
    syncCount: 0,
    maxLagMs: maxLagMs,
    maxDivergenceM: maxDivM,
    eventCounter: 0,
  )

proc registerTwin*(mgr: var DigitalTwinManager, twinId: string) =
  mgr.twins[twinId] = TwinState(
    twinId: twinId,
    status: Disconnected,
  )

proc updatePhysical*(mgr: var DigitalTwinManager, twinId: string,
                     pos: Vec3, vel: Vec3, timestamp: float64) =
  if twinId in mgr.twins:
    mgr.twins[twinId].physicalPos = pos
    mgr.twins[twinId].physicalVel = vel
    mgr.twins[twinId].syncTimestamp = timestamp

proc predict*(mgr: DigitalTwinManager, twinId: string, dt: float64): Vec3 =
  if twinId in mgr.twins:
    let twin = mgr.twins[twinId]
    result = twin.physicalPos + twin.physicalVel * dt
  else:
    result = Vec3(x: 0, y: 0, z: 0)

proc sync*(mgr: var DigitalTwinManager, twinId: string,
           currentTime: float64): TwinStatus =
  if twinId notin mgr.twins:
    return Disconnected

  mgr.syncCount += 1
  var twin = mgr.twins[twinId]
  twin.lagMs = (currentTime - twin.syncTimestamp) * 1000.0
  twin.divergence = distance(twin.physicalPos, twin.digitalPos)

  if twin.lagMs > mgr.maxLagMs:
    twin.status = Disconnected
  elif twin.divergence > mgr.maxDivergenceM:
    twin.status = Lagging
    twin.digitalPos = twin.physicalPos  # force sync
  elif twin.lagMs > 100.0:
    twin.status = Predicted
    twin.digitalPos = twin.physicalPos + twin.physicalVel * (twin.lagMs / 1000.0)
  else:
    twin.status = Synced
    twin.digitalPos = twin.physicalPos

  mgr.twins[twinId] = twin
  mgr.eventCounter += 1
  mgr.events.add(SyncEvent(
    eventId: fmt"SYNC-{mgr.eventCounter:06d}",
    twinId: twinId,
    eventType: "state_update",
    timestamp: currentTime,
  ))
  return twin.status

proc syncAll*(mgr: var DigitalTwinManager, currentTime: float64): seq[(string, TwinStatus)] =
  result = @[]
  for id in mgr.twins.keys:
    let status = mgr.sync(id, currentTime)
    result.add((id, status))

proc getDivergentTwins*(mgr: DigitalTwinManager, threshold: float64 = 2.0): seq[string] =
  result = @[]
  for id, twin in mgr.twins:
    if twin.divergence > threshold:
      result.add(id)

proc summary*(mgr: DigitalTwinManager): string =
  var statusCounts: Table[TwinStatus, int] = initTable[TwinStatus, int]()
  for _, twin in mgr.twins:
    if twin.status in statusCounts:
      statusCounts[twin.status] += 1
    else:
      statusCounts[twin.status] = 1
  let n = max(mgr.twins.len, 1)
  fmt"Twins: {mgr.twins.len}, Syncs: {mgr.syncCount}, Events: {mgr.events.len}"

# ── Main (example usage) ────────────────────────────────────────
when isMainModule:
  var mgr = newDigitalTwinManager()
  mgr.registerTwin("drone_1")
  mgr.registerTwin("drone_2")

  mgr.updatePhysical("drone_1", Vec3(x: 10, y: 20, z: 50),
                      Vec3(x: 1, y: 0, z: 0), 1.0)
  mgr.updatePhysical("drone_2", Vec3(x: 30, y: 40, z: 60),
                      Vec3(x: -1, y: 1, z: 0), 1.0)

  let results = mgr.syncAll(1.05)
  for (id, status) in results:
    echo fmt"  {id}: {status}"

  echo mgr.summary()
