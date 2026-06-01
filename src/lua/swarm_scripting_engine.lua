-- Phase 553: Swarm Scripting Engine — 군집 드론 Lua 스크립팅 엔진
-- Mission scripting engine: event-driven drone control via Lua DSL.

local SwarmScriptingEngine = {}
SwarmScriptingEngine.__index = SwarmScriptingEngine

-- ── Event system ─────────────────────────────────────────────────

local EventBus = {}
EventBus.__index = EventBus

function EventBus.new()
    return setmetatable({listeners = {}, history = {}}, EventBus)
end

function EventBus:subscribe(event_type, handler)
    if not self.listeners[event_type] then
        self.listeners[event_type] = {}
    end
    table.insert(self.listeners[event_type], handler)
end

--- Emit dispatches an Event to all registered handlers.
function EventBus:emit(event_type, data)
    local ev = {type = event_type, data = data, ts = os.clock()}
    table.insert(self.history, ev)
    local handlers = self.listeners[event_type] or {}
    for _, h in ipairs(handlers) do
        h(ev)
    end
end

-- ── Mission definition ────────────────────────────────────────────

local Mission = {}
Mission.__index = Mission

function Mission.new(id, waypoints)
    return setmetatable({
        id        = id,
        waypoints = waypoints or {},
        status    = "pending",
        current_wp = 1,
        events    = {},
    }, Mission)
end

function Mission:add_waypoint(x, y, z)
    table.insert(self.waypoints, {x=x, y=y, z=z})
end

function Mission:next_waypoint()
    if self.current_wp <= #self.waypoints then
        local wp = self.waypoints[self.current_wp]
        self.current_wp = self.current_wp + 1
        return wp
    end
    self.status = "complete"
    return nil
end

-- ── Drone agent ────────────────────────────────────────────────────

local DroneAgent = {}
DroneAgent.__index = DroneAgent

function DroneAgent.new(id, bus)
    return setmetatable({
        id       = id,
        x = 0, y = 0, z = 0,
        battery  = 100,
        status   = "idle",
        mission  = nil,
        bus      = bus,
    }, DroneAgent)
end

function DroneAgent:assign_mission(m)
    self.mission = m
    self.status = "active"
    self.bus:emit("mission_assigned", {drone=self.id, mission=m.id})
end

function DroneAgent:step()
    if not self.mission or self.mission.status == "complete" then
        self.status = "idle"
        return
    end
    local wp = self.mission:next_waypoint()
    if wp then
        self.x = wp.x; self.y = wp.y; self.z = wp.z
        self.battery = self.battery - 1
        self.bus:emit("waypoint_reached", {drone=self.id, wp=wp})
    end
end

-- ── Scripting Engine ──────────────────────────────────────────────

function SwarmScriptingEngine.new(n_drones)
    local bus    = EventBus.new()
    local drones = {}
    for i = 1, n_drones do
        drones[i] = DroneAgent.new("drone_" .. i, bus)
    end
    return setmetatable({
        drones   = drones,
        bus      = bus,
        missions = {},
        tick     = 0,
    }, SwarmScriptingEngine)
end

function SwarmScriptingEngine:create_mission(id, wps)
    local m = Mission.new(id, wps)
    table.insert(self.missions, m)
    return m
end

function SwarmScriptingEngine:assign(drone_idx, mission)
    self.drones[drone_idx]:assign_mission(mission)
end

function SwarmScriptingEngine:step()
    self.tick = self.tick + 1
    for _, d in ipairs(self.drones) do
        d:step()
    end
end

function SwarmScriptingEngine:run(steps)
    for _ = 1, steps do
        self:step()
    end
end

function SwarmScriptingEngine:summary()
    local active = 0
    for _, d in ipairs(self.drones) do
        if d.status == "active" then active = active + 1 end
    end
    return {
        tick         = self.tick,
        total_drones = #self.drones,
        active       = active,
        events       = #self.bus.history,
        phase        = 553,
    }
end

-- ── Entry point ────────────────────────────────────────────────────

local engine = SwarmScriptingEngine.new(5)
local m1 = engine:create_mission("mission_alpha", {
    {x=10, y=20, z=50},
    {x=30, y=40, z=60},
    {x=50, y=50, z=50},
})
engine:assign(1, m1)
engine:run(5)
local s = engine:summary()
print(string.format("Phase %d: tick=%d, active=%d, events=%d",
    s.phase, s.tick, s.active, s.events))

return SwarmScriptingEngine
