-- Phase 553 — Swarm Scripting Engine: Mission and Event System
-- Lua module for dynamic mission scripting and event-driven drone behavior.

-- ===== Event System =====

local EventBus = {}
EventBus.__index = EventBus

--- Create a new event bus
function EventBus.new()
    return setmetatable({
        listeners = {},
        event_log = {},
        event_count = 0
    }, EventBus)
end

--- Subscribe a handler to an event type
function EventBus:subscribe(event_type, handler)
    if not self.listeners[event_type] then
        self.listeners[event_type] = {}
    end
    table.insert(self.listeners[event_type], handler)
end

--- Emit an event to all subscribed handlers
function EventBus:emit(event_type, data)
    self.event_count = self.event_count + 1
    local event = {
        id = self.event_count,
        type = event_type,
        data = data,
        timestamp = os.time()
    }
    table.insert(self.event_log, event)
    local handlers = self.listeners[event_type] or {}
    for _, handler in ipairs(handlers) do
        handler(event)
    end
    return event
end

--- Get all events of a given type
function EventBus:get_events(event_type)
    local result = {}
    for _, e in ipairs(self.event_log) do
        if e.type == event_type then
            table.insert(result, e)
        end
    end
    return result
end

-- ===== Mission System =====

local Mission = {}
Mission.__index = Mission

--- Available mission states
local MissionState = {
    PENDING  = "PENDING",
    ACTIVE   = "ACTIVE",
    PAUSED   = "PAUSED",
    COMPLETE = "COMPLETE",
    FAILED   = "FAILED"
}

--- Create a new mission
function Mission.new(id, name, drone_ids, waypoints)
    return setmetatable({
        id = id,
        name = name,
        drone_ids = drone_ids or {},
        waypoints = waypoints or {},
        state = MissionState.PENDING,
        current_wp = 1,
        start_time = nil,
        end_time = nil,
        events = {}
    }, Mission)
end

--- Start the mission
function Mission:start(event_bus)
    if self.state ~= MissionState.PENDING then
        return false, "Mission not in PENDING state"
    end
    self.state = MissionState.ACTIVE
    self.start_time = os.time()
    event_bus:emit("mission_started", { mission_id = self.id, name = self.name })
    return true, "Mission started"
end

--- Advance to next waypoint
function Mission:advance_waypoint(event_bus)
    if self.state ~= MissionState.ACTIVE then return false end
    if self.current_wp >= #self.waypoints then
        self.state = MissionState.COMPLETE
        self.end_time = os.time()
        event_bus:emit("mission_complete", { mission_id = self.id })
        return false
    end
    self.current_wp = self.current_wp + 1
    event_bus:emit("waypoint_reached", {
        mission_id = self.id,
        waypoint = self.current_wp,
        total = #self.waypoints
    })
    return true
end

--- Pause or resume the mission
function Mission:pause(event_bus)
    if self.state == MissionState.ACTIVE then
        self.state = MissionState.PAUSED
        event_bus:emit("mission_paused", { mission_id = self.id })
    elseif self.state == MissionState.PAUSED then
        self.state = MissionState.ACTIVE
        event_bus:emit("mission_resumed", { mission_id = self.id })
    end
end

--- Abort the mission
function Mission:abort(reason, event_bus)
    self.state = MissionState.FAILED
    self.end_time = os.time()
    event_bus:emit("mission_aborted", { mission_id = self.id, reason = reason })
end

--- Get mission summary
function Mission:summary()
    return {
        id = self.id,
        name = self.name,
        state = self.state,
        progress = self.current_wp .. "/" .. #self.waypoints,
        drones = #self.drone_ids
    }
end

-- ===== Mission Manager =====

local MissionManager = {}
MissionManager.__index = MissionManager

function MissionManager.new()
    return setmetatable({
        missions = {},
        event_bus = EventBus.new(),
        active_count = 0
    }, MissionManager)
end

function MissionManager:add_mission(mission)
    self.missions[mission.id] = mission
end

function MissionManager:start_mission(mission_id)
    local m = self.missions[mission_id]
    if not m then return false, "Mission not found" end
    local ok, msg = m:start(self.event_bus)
    if ok then self.active_count = self.active_count + 1 end
    return ok, msg
end

function MissionManager:tick_all()
    for _, m in pairs(self.missions) do
        if m.state == MissionState.ACTIVE then
            m:advance_waypoint(self.event_bus)
        end
    end
end

function MissionManager:stats()
    local total = 0
    local complete = 0
    for _, m in pairs(self.missions) do
        total = total + 1
        if m.state == MissionState.COMPLETE then
            complete = complete + 1
        end
    end
    return {
        total = total,
        complete = complete,
        events = self.event_bus.event_count
    }
end

-- ===== Main Execution =====

print("Phase 553: Swarm Scripting Engine - Mission and Event System")

local manager = MissionManager.new()

-- Subscribe to key events
manager.event_bus:subscribe("mission_started", function(e)
    print("  [EVENT] Mission started: " .. e.data.name)
end)
manager.event_bus:subscribe("waypoint_reached", function(e)
    print("  [EVENT] Waypoint " .. e.data.waypoint .. "/" .. e.data.total)
end)
manager.event_bus:subscribe("mission_complete", function(e)
    print("  [EVENT] Mission COMPLETE: " .. e.data.mission_id)
end)

-- Create missions
local wp1 = {{x=0,y=0,z=50},{x=10,y=5,z=55},{x=20,y=0,z=50}}
local m1 = Mission.new("M001", "Patrol Alpha", {"D1","D2"}, wp1)
local m2 = Mission.new("M002", "Survey Beta",  {"D3"},     {{x=5,y=5,z=60},{x=15,y=10,z=65}})

manager:add_mission(m1)
manager:add_mission(m2)
manager:start_mission("M001")
manager:start_mission("M002")

-- Run mission steps
for i = 1, 5 do
    manager:tick_all()
end

local stats = manager:stats()
print("Total missions: " .. stats.total)
print("Completed: " .. stats.complete)
print("Events fired: " .. stats.events)
