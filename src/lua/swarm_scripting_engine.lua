-- P553: SwarmScriptingEngine - Lua scripting for swarm missions
-- Phase 553: Event-driven mission scripting for drone fleet control

local M = {}

-- Event types
M.EventType = {
    MISSION_START   = "MISSION_START",
    MISSION_END     = "MISSION_END",
    DRONE_ARRIVED   = "DRONE_ARRIVED",
    CONFLICT        = "CONFLICT",
    BATTERY_LOW     = "BATTERY_LOW",
    WAYPOINT_REACHED= "WAYPOINT_REACHED",
}

-- Mission state
local Mission = {}
Mission.__index = Mission

function Mission.new(name, params)
    local self = setmetatable({}, Mission)
    self.name         = name
    self.params       = params or {}
    self.state        = "PENDING"
    self.events       = {}
    self.handlers     = {}
    self.waypoints    = {}
    self.drones       = {}
    self.start_time   = nil
    self.end_time     = nil
    return self
end

function Mission:on(event_type, handler)
    if not self.handlers[event_type] then
        self.handlers[event_type] = {}
    end
    table.insert(self.handlers[event_type], handler)
end

function Mission:emit(event_type, data)
    local event = {
        type      = event_type,
        data      = data or {},
        timestamp = os.time(),
    }
    table.insert(self.events, event)
    if self.handlers[event_type] then
        for _, handler in ipairs(self.handlers[event_type]) do
            handler(event)
        end
    end
end

function Mission:add_waypoint(wp)
    table.insert(self.waypoints, {
        x    = wp.x or 0,
        y    = wp.y or 0,
        z    = wp.z or 60,
        name = wp.name or ("WP" .. #self.waypoints + 1),
    })
end

function Mission:assign_drone(drone_id)
    self.drones[drone_id] = { status = "ASSIGNED", progress = 0 }
end

function Mission:start()
    self.state      = "RUNNING"
    self.start_time = os.time()
    self:emit(M.EventType.MISSION_START, { mission = self.name })
end

function Mission:complete()
    self.state    = "COMPLETED"
    self.end_time = os.time()
    self:emit(M.EventType.MISSION_END, {
        mission  = self.name,
        duration = self.end_time - (self.start_time or self.end_time),
    })
end

function Mission:abort(reason)
    self.state    = "ABORTED"
    self.end_time = os.time()
    self:emit(M.EventType.MISSION_END, { mission = self.name, reason = reason })
end

-- Script engine
local Engine = {}
Engine.__index = Engine

function Engine.new()
    local self = setmetatable({}, Engine)
    self.missions  = {}
    self.scripts   = {}
    return self
end

function Engine:load_script(name, script_fn)
    self.scripts[name] = script_fn
end

function Engine:create_mission(name, params)
    local mission = Mission.new(name, params)
    self.missions[name] = mission
    if self.scripts[name] then
        self.scripts[name](mission)
    end
    return mission
end

function Engine:get_mission(name)
    return self.missions[name]
end

M.Mission = Mission
M.Engine  = Engine

return M
