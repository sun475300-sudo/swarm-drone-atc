-- swarm_scripting_engine.lua - Scripting engine for SDACS (Phase 553)
-- Lua-based mission scripting and event handling for drone swarm

local SwarmEngine = {}
SwarmEngine.__index = SwarmEngine

-- Mission state machine
local MissionState = {
    IDLE        = "idle",
    RUNNING     = "running",
    PAUSED      = "paused",
    COMPLETED   = "completed",
    FAILED      = "failed",
}

-- Mission definition
function SwarmEngine.new_mission(name, waypoints, options)
    return {
        name        = name,
        state       = MissionState.IDLE,
        waypoints   = waypoints or {},
        current_wp  = 1,
        drones      = {},
        start_time  = nil,
        end_time    = nil,
        options     = options or {},
    }
end

-- Event system
local EventBus = {}
EventBus.__index = EventBus

function EventBus.new()
    local bus = setmetatable({ handlers = {} }, EventBus)
    return bus
end

function EventBus:on(event_name, handler)
    if not self.handlers[event_name] then
        self.handlers[event_name] = {}
    end
    table.insert(self.handlers[event_name], handler)
end

function EventBus:emit(event_name, data)
    local handlers = self.handlers[event_name] or {}
    for _, handler in ipairs(handlers) do
        local ok, err = pcall(handler, data)
        if not ok then
            print("[EventBus] Error in handler for '" .. event_name .. "': " .. tostring(err))
        end
    end
end

-- Scripting context for mission execution
function SwarmEngine.new(n_drones, seed)
    local engine = setmetatable({
        n_drones    = n_drones or 10,
        seed        = seed or 42,
        missions    = {},
        event_bus   = EventBus.new(),
        tick        = 0,
        drones      = {},
    }, SwarmEngine)

    -- Initialize drone fleet
    math.randomseed(seed or 42)
    for i = 1, engine.n_drones do
        engine.drones[i] = {
            id       = string.format("D-%03d", i),
            x        = math.random(-500, 500),
            y        = math.random(-500, 500),
            z        = math.random(20, 120),
            battery  = math.random(50, 100),
            status   = "idle",
        }
    end

    return engine
end

function SwarmEngine:register_mission(mission)
    table.insert(self.missions, mission)
    self.event_bus:emit("mission_registered", { mission = mission })
end

function SwarmEngine:start_mission(mission_name)
    for _, m in ipairs(self.missions) do
        if m.name == mission_name then
            m.state = MissionState.RUNNING
            m.start_time = os.time()
            self.event_bus:emit("mission_started", { mission = m })
            return true
        end
    end
    return false
end

function SwarmEngine:on_event(event_name, handler)
    self.event_bus:on(event_name, handler)
end

function SwarmEngine:update(dt)
    self.tick = self.tick + 1
    -- Update drone positions
    for _, drone in ipairs(self.drones) do
        drone.battery = math.max(0, drone.battery - 0.01 * dt)
        if drone.battery < 10 then
            drone.status = "returning"
            self.event_bus:emit("low_battery", { drone_id = drone.id, battery = drone.battery })
        end
    end
    self.event_bus:emit("tick", { tick = self.tick, drones = #self.drones })
end

function SwarmEngine:get_status()
    local active = 0
    for _, d in ipairs(self.drones) do
        if d.status == "active" or d.status == "idle" then active = active + 1 end
    end
    return {
        tick         = self.tick,
        total_drones = #self.drones,
        active       = active,
        missions     = #self.missions,
    }
end

-- Phase 553 marker
SwarmEngine._phase = 553

print("SDACS Swarm Scripting Engine (Phase 553) loaded")
return SwarmEngine
