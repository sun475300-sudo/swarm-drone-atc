-- Phase 553: Swarm Scripting Engine — Lua
-- SDACS mission scripting interpreter for drone swarm behavior programming

-- Phase 553 marker — Mission/Event scripting engine for drone swarms

local SwarmEngine = {}
SwarmEngine.__index = SwarmEngine

-- Event types
local EVENT_TYPES = {
    MISSION_START   = "mission_start",
    MISSION_END     = "mission_end",
    WAYPOINT_REACHED = "waypoint_reached",
    BATTERY_LOW     = "battery_low",
    CONFLICT        = "conflict",
    DRONE_JOINED    = "drone_joined",
    DRONE_LEFT      = "drone_left",
    COMMAND         = "command",
    TELEMETRY       = "telemetry",
}

-- Create a new swarm scripting engine
function SwarmEngine.new()
    local self = setmetatable({}, SwarmEngine)
    self.drones       = {}
    self.missions     = {}
    self.handlers     = {}
    self.event_queue  = {}
    self.tick_count   = 0
    self.globals      = {}
    self.plugins      = {}
    return self
end

-- Register an event handler
function SwarmEngine:on(event_type, handler_fn)
    if not self.handlers[event_type] then
        self.handlers[event_type] = {}
    end
    table.insert(self.handlers[event_type], handler_fn)
end

-- Emit an event
function SwarmEngine:emit(event_type, data)
    local event = {
        type      = event_type,
        data      = data or {},
        timestamp = self.tick_count,
    }
    table.insert(self.event_queue, event)
end

-- Process all queued events
function SwarmEngine:process_events()
    local processed = 0
    while #self.event_queue > 0 do
        local event = table.remove(self.event_queue, 1)
        local handlers = self.handlers[event.type] or {}
        for _, handler in ipairs(handlers) do
            local ok, err = pcall(handler, event)
            if not ok then
                print("[ERROR] Event handler failed for " .. event.type .. ": " .. tostring(err))
            end
        end
        processed = processed + 1
    end
    return processed
end

-- Register a drone
function SwarmEngine:add_drone(id, config)
    self.drones[id] = {
        id       = id,
        lat      = config.lat or 0,
        lon      = config.lon or 0,
        alt      = config.alt or 0,
        speed    = config.speed or 10,
        battery  = config.battery or 100,
        mode     = "idle",
        waypoints = {},
    }
    self:emit(EVENT_TYPES.DRONE_JOINED, { drone_id = id })
    return self.drones[id]
end

-- Remove a drone
function SwarmEngine:remove_drone(id)
    if self.drones[id] then
        self:emit(EVENT_TYPES.DRONE_LEFT, { drone_id = id })
        self.drones[id] = nil
    end
end

-- Mission definition
function SwarmEngine:define_mission(name, script_fn)
    self.missions[name] = {
        name      = name,
        script    = script_fn,
        state     = "ready",
        progress  = 0,
    }
end

-- Execute a mission
function SwarmEngine:run_mission(name, context)
    local mission = self.missions[name]
    if not mission then
        return nil, "Mission not found: " .. name
    end
    mission.state = "running"
    self:emit(EVENT_TYPES.MISSION_START, { mission = name, context = context })
    local ok, err = pcall(mission.script, self, context or {})
    if ok then
        mission.state = "completed"
        self:emit(EVENT_TYPES.MISSION_END, { mission = name, success = true })
        return true
    else
        mission.state = "failed"
        self:emit(EVENT_TYPES.MISSION_END, { mission = name, success = false, error = err })
        return false, err
    end
end

-- Send command to drone
function SwarmEngine:command(drone_id, cmd, params)
    local drone = self.drones[drone_id]
    if not drone then return false end
    self:emit(EVENT_TYPES.COMMAND, { drone_id = drone_id, command = cmd, params = params })
    if cmd == "TAKEOFF" then
        drone.mode = "flying"
        drone.alt  = params and params.alt or 60
    elseif cmd == "LAND" then
        drone.mode = "landing"
        drone.alt  = 0
    elseif cmd == "RTL" then
        drone.mode = "rtl"
    elseif cmd == "GOTO" then
        if params then
            table.insert(drone.waypoints, { lat = params.lat, lon = params.lon, alt = params.alt })
        end
    end
    return true
end

-- Update telemetry
function SwarmEngine:update_telemetry(drone_id, telem)
    local drone = self.drones[drone_id]
    if not drone then return end
    for k, v in pairs(telem) do drone[k] = v end
    self:emit(EVENT_TYPES.TELEMETRY, { drone_id = drone_id, data = telem })
    if drone.battery and drone.battery < 20 then
        self:emit(EVENT_TYPES.BATTERY_LOW, { drone_id = drone_id, battery = drone.battery })
    end
end

-- Tick simulation forward
function SwarmEngine:tick(dt)
    self.tick_count = self.tick_count + 1
    dt = dt or 0.1
    -- Update drone positions (simple forward integration)
    for id, drone in pairs(self.drones) do
        if drone.mode == "flying" and #drone.waypoints > 0 then
            -- Move toward next waypoint (simplified)
            local wp = drone.waypoints[1]
            local dlat = wp.lat - drone.lat
            local dlon = wp.lon - drone.lon
            local dist = math.sqrt(dlat^2 + dlon^2) * 111000  -- approx meters
            if dist < 5.0 then
                table.remove(drone.waypoints, 1)
                self:emit(EVENT_TYPES.WAYPOINT_REACHED, { drone_id = id })
            else
                local step = drone.speed * dt / dist
                drone.lat = drone.lat + dlat * step
                drone.lon = drone.lon + dlon * step
            end
        end
        if drone.battery then
            drone.battery = math.max(0, drone.battery - 0.01 * dt)
        end
    end
    return self:process_events()
end

-- Statistics
function SwarmEngine:stats()
    local count = 0
    for _ in pairs(self.drones) do count = count + 1 end
    return {
        drones    = count,
        missions  = #(function() local t={}; for k in pairs(self.missions) do t[#t+1]=k end; return t end)(),
        tick      = self.tick_count,
        events_processed = self.tick_count,  -- approximate
    }
end

-- Plugin system
function SwarmEngine:use_plugin(plugin)
    if plugin.install then
        plugin.install(self)
    end
    self.plugins[plugin.name] = plugin
end

-- Export module
return SwarmEngine
