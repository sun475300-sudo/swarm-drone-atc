-- Phase 553: Lua Lightweight Scripting Engine for Drone Control
-- 경량 스크립팅: 미션 DSL, 조건 기반 행동 트리, 이벤트 트리거

local PRNG = {}
PRNG.__index = PRNG

function PRNG.new(seed)
    local self = setmetatable({}, PRNG)
    self.state = (seed or 42) ~ 0x6c62272e  -- XOR
    return self
end

function PRNG:next()
    self.state = self.state ~ (self.state << 13)
    self.state = self.state ~ (self.state >> 7)
    self.state = self.state ~ (self.state << 17)
    return math.abs(self.state)
end

function PRNG:uniform()
    return (self:next() % 10000) / 10000.0
end

-- Drone state
local Drone = {}
Drone.__index = Drone

function Drone.new(id, rng)
    local self = setmetatable({}, Drone)
    self.id = id
    self.x = rng:uniform() * 100 - 50
    self.y = rng:uniform() * 100 - 50
    self.z = 30 + rng:uniform() * 70
    self.battery = 80 + rng:uniform() * 20
    self.status = "idle"
    self.mission = nil
    self.log = {}
    return self
end

function Drone:execute(cmd)
    table.insert(self.log, cmd)
    if cmd.action == "move" then
        self.x = self.x + (cmd.dx or 0)
        self.y = self.y + (cmd.dy or 0)
        self.z = self.z + (cmd.dz or 0)
        self.battery = self.battery - 0.5
    elseif cmd.action == "hover" then
        self.battery = self.battery - 0.1
    elseif cmd.action == "land" then
        self.z = 0
        self.status = "landed"
    elseif cmd.action == "takeoff" then
        self.z = 50
        self.status = "flying"
    end
end

-- Mission DSL
local Mission = {}
Mission.__index = Mission

function Mission.new(name)
    local self = setmetatable({}, Mission)
    self.name = name
    self.steps = {}
    self.current = 1
    return self
end

function Mission:add_step(step)
    table.insert(self.steps, step)
end

function Mission:next_step()
    if self.current <= #self.steps then
        local step = self.steps[self.current]
        self.current = self.current + 1
        return step
    end
    return nil
end

function Mission:is_complete()
    return self.current > #self.steps
end

-- Behavior Tree nodes
local function condition_node(check_fn)
    return function(drone)
        return check_fn(drone)
    end
end

local function action_node(action_fn)
    return function(drone)
        action_fn(drone)
        return true
    end
end

local function sequence(nodes)
    return function(drone)
        for _, node in ipairs(nodes) do
            if not node(drone) then return false end
        end
        return true
    end
end

-- Event system
local EventSystem = {}
EventSystem.__index = EventSystem

function EventSystem.new()
    local self = setmetatable({}, EventSystem)
    self.listeners = {}
    self.events_fired = 0
    return self
end

function EventSystem:on(event, callback)
    if not self.listeners[event] then
        self.listeners[event] = {}
    end
    table.insert(self.listeners[event], callback)
end

function EventSystem:fire(event, data)
    self.events_fired = self.events_fired + 1
    if self.listeners[event] then
        for _, cb in ipairs(self.listeners[event]) do
            cb(data)
        end
    end
end

-- Main simulation
local function main()
    local rng = PRNG.new(42)
    local n_drones = 8
    local drones = {}
    local events = EventSystem.new()
    local missions_completed = 0

    -- Create drones
    for i = 1, n_drones do
        drones[i] = Drone.new("drone_" .. (i-1), rng)
    end

    -- Setup events
    events:on("low_battery", function(data)
        data.drone:execute({action = "land"})
    end)

    events:on("mission_complete", function(data)
        missions_completed = missions_completed + 1
    end)

    -- Create missions
    for _, drone in ipairs(drones) do
        local m = Mission.new("patrol_" .. drone.id)
        m:add_step({action = "takeoff"})
        for j = 1, 3 do
            m:add_step({action = "move", dx = rng:uniform() * 10 - 5, dy = rng:uniform() * 10 - 5, dz = 0})
        end
        m:add_step({action = "hover"})
        m:add_step({action = "land"})
        drone.mission = m
    end

    -- Run simulation
    for step = 1, 20 do
        for _, drone in ipairs(drones) do
            if drone.mission and not drone.mission:is_complete() then
                local cmd = drone.mission:next_step()
                if cmd then drone:execute(cmd) end
            else
                events:fire("mission_complete", {drone = drone})
                drone.mission = nil
            end

            if drone.battery < 15 then
                events:fire("low_battery", {drone = drone})
            end
        end
    end

    print("Drones: " .. #drones)
    print("Missions completed: " .. missions_completed)
    print("Events fired: " .. events.events_fired)
    local total_cmds = 0
    for _, d in ipairs(drones) do total_cmds = total_cmds + #d.log end
    print("Total commands: " .. total_cmds)
end

main()
