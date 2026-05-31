-- Phase 553 — Lua scripting engine for mission definition and event-driven behavior
-- Provides a lightweight sandboxed environment for drone mission scripts.

local SwarmScriptingEngine = {}
SwarmScriptingEngine.__index = SwarmScriptingEngine

-- ── Constants ────────────────────────────────────────────────────────────────

local VERSION = "553"
local MAX_MISSIONS = 64
local MAX_EVENTS_PER_TICK = 32

-- ── Event types ──────────────────────────────────────────────────────────────

local EventType = {
  MISSION_START    = "mission_start",
  MISSION_COMPLETE = "mission_complete",
  WAYPOINT_REACHED = "waypoint_reached",
  COLLISION_ALERT  = "collision_alert",
  LOW_BATTERY      = "low_battery",
  GEOFENCE_BREACH  = "geofence_breach",
  DRONE_LOST       = "drone_lost",
  CUSTOM           = "custom",
}

-- ── Mission definition ───────────────────────────────────────────────────────

local function new_mission(id, name, droneIds)
  return {
    id        = id,
    name      = name,
    droneIds  = droneIds or {},
    waypoints = {},
    handlers  = {},   -- event -> list of callbacks
    status    = "pending",   -- pending | active | complete | aborted
    startTime = nil,
    endTime   = nil,
    metadata  = {},
  }
end

local function mission_add_waypoint(mission, x, y, z, holdSecs)
  local wp = {
    index    = #mission.waypoints + 1,
    x        = x,
    y        = y,
    z        = z,
    holdSecs = holdSecs or 0,
    reached  = false,
  }
  table.insert(mission.waypoints, wp)
  return wp
end

-- ── Event bus ────────────────────────────────────────────────────────────────

local EventBus = {}
EventBus.__index = EventBus

function EventBus.new()
  local self = setmetatable({}, EventBus)
  self._queue    = {}
  self._handlers = {}
  return self
end

function EventBus:subscribe(eventType, callback)
  if not self._handlers[eventType] then
    self._handlers[eventType] = {}
  end
  table.insert(self._handlers[eventType], callback)
end

function EventBus:publish(eventType, payload)
  table.insert(self._queue, { type = eventType, payload = payload, ts = os.time() })
end

function EventBus:flush(maxEvents)
  local count = 0
  while #self._queue > 0 and count < (maxEvents or MAX_EVENTS_PER_TICK) do
    local evt = table.remove(self._queue, 1)
    local handlers = self._handlers[evt.type] or {}
    for _, cb in ipairs(handlers) do
      local ok, err = pcall(cb, evt.payload, evt.ts)
      if not ok then
        io.stderr:write(string.format("[553] event handler error (%s): %s\n", evt.type, tostring(err)))
      end
    end
    count = count + 1
  end
  return count
end

-- ── Scripting Engine ─────────────────────────────────────────────────────────

function SwarmScriptingEngine.new()
  local self = setmetatable({}, SwarmScriptingEngine)
  self.version  = VERSION
  self.missions = {}
  self.bus      = EventBus.new()
  self._nextId  = 1
  return self
end

function SwarmScriptingEngine:createMission(name, droneIds)
  assert(#self.missions < MAX_MISSIONS, "[553] Mission limit reached")
  local id      = string.format("MISSION-%03d", self._nextId)
  self._nextId  = self._nextId + 1
  local mission = new_mission(id, name, droneIds)
  self.missions[id] = mission
  return mission
end

function SwarmScriptingEngine:addWaypoint(missionId, x, y, z, holdSecs)
  local mission = self.missions[missionId]
  assert(mission, "[553] Unknown mission: " .. tostring(missionId))
  return mission_add_waypoint(mission, x, y, z, holdSecs)
end

function SwarmScriptingEngine:onEvent(missionId, eventType, callback)
  local mission = self.missions[missionId]
  assert(mission, "[553] Unknown mission: " .. tostring(missionId))
  if not mission.handlers[eventType] then
    mission.handlers[eventType] = {}
  end
  table.insert(mission.handlers[eventType], callback)
  -- also wire into global bus
  self.bus:subscribe(eventType, function(payload, ts)
    if payload.missionId == missionId then
      callback(payload, ts)
    end
  end)
end

function SwarmScriptingEngine:startMission(missionId)
  local mission = self.missions[missionId]
  assert(mission, "[553] Unknown mission: " .. tostring(missionId))
  mission.status    = "active"
  mission.startTime = os.time()
  self.bus:publish(EventType.MISSION_START, { missionId = missionId, mission = mission })
  print(string.format("[553] Mission started: %s (%s)", mission.name, missionId))
end

function SwarmScriptingEngine:completeMission(missionId)
  local mission = self.missions[missionId]
  if not mission then return end
  mission.status  = "complete"
  mission.endTime = os.time()
  self.bus:publish(EventType.MISSION_COMPLETE, { missionId = missionId })
  print(string.format("[553] Mission complete: %s", missionId))
end

function SwarmScriptingEngine:tick()
  return self.bus:flush()
end

function SwarmScriptingEngine:status()
  local counts = { pending=0, active=0, complete=0, aborted=0 }
  for _, m in pairs(self.missions) do
    counts[m.status] = (counts[m.status] or 0) + 1
  end
  return counts
end

-- ── Demo ─────────────────────────────────────────────────────────────────────

local engine  = SwarmScriptingEngine.new()
local mission = engine:createMission("Patrol Alpha", {"D001", "D002"})

engine:addWaypoint(mission.id,  0,  0, 20)
engine:addWaypoint(mission.id, 50,  0, 20)
engine:addWaypoint(mission.id, 50, 50, 20)
engine:addWaypoint(mission.id,  0, 50, 20)

engine:onEvent(mission.id, EventType.MISSION_START, function(payload, ts)
  print(string.format("[553] Handler fired: mission_start at t=%d", ts))
end)

engine:startMission(mission.id)
engine:tick()
engine:completeMission(mission.id)
engine:tick()

local s = engine:status()
print(string.format("[553] Engine v%s status — active=%d complete=%d", VERSION, s.active, s.complete))

return SwarmScriptingEngine
