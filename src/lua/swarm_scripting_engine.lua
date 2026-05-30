-- SDACS Swarm Scripting Engine — Lua (Phase 553)
-- 드론 군집 임무(Mission) 스크립팅 엔진

local ScriptingEngine = {}
ScriptingEngine.__index = ScriptingEngine

-- Event 타입 정의
local EventTypes = {
    MISSION_START  = "mission_start",
    MISSION_END    = "mission_end",
    WAYPOINT_REACH = "waypoint_reached",
    CONFLICT       = "conflict_detected",
    BATTERY_LOW    = "battery_low",
    EMERGENCY      = "emergency",
}

-- Mission 객체
local Mission = {}
Mission.__index = Mission

function Mission.new(id, name, waypoints)
    return setmetatable({
        id       = id,
        name     = name,
        waypoints = waypoints or {},
        status   = "pending",
        created  = os.time(),
        events   = {},
    }, Mission)
end

function Mission:start()
    self.status = "running"
    self:emit(EventTypes.MISSION_START, {mission_id = self.id})
end

function Mission:complete()
    self.status = "completed"
    self:emit(EventTypes.MISSION_END, {mission_id = self.id, status = "success"})
end

function Mission:emit(event_type, data)
    table.insert(self.events, {
        type = event_type,
        data = data or {},
        timestamp = os.time(),
    })
end

function Mission:waypointCount()
    return #self.waypoints
end

-- Event 버스
local EventBus = {}
EventBus.__index = EventBus

function EventBus.new()
    return setmetatable({ handlers = {}, history = {} }, EventBus)
end

function EventBus:subscribe(event_type, handler)
    if not self.handlers[event_type] then
        self.handlers[event_type] = {}
    end
    table.insert(self.handlers[event_type], handler)
end

function EventBus:emit(event_type, data)
    table.insert(self.history, { type = event_type, data = data, ts = os.time() })
    for _, handler in ipairs(self.handlers[event_type] or {}) do
        handler(data)
    end
end

function EventBus:historyCount()
    return #self.history
end

-- 스크립팅 엔진 (Phase 553)
function ScriptingEngine.new()
    local self = setmetatable({
        missions    = {},
        event_bus   = EventBus.new(),
        variables   = {},
        running     = false,
    }, ScriptingEngine)
    return self
end

function ScriptingEngine:addMission(mission)
    self.missions[mission.id] = mission
end

function ScriptingEngine:getMission(id)
    return self.missions[id]
end

function ScriptingEngine:runMission(id)
    local m = self.missions[id]
    if not m then return false, "Mission not found: " .. id end
    m:start()
    self.event_bus:emit(EventTypes.MISSION_START, {id = id, name = m.name})
    for i, wp in ipairs(m.waypoints) do
        self.event_bus:emit(EventTypes.WAYPOINT_REACH, {waypoint = i, pos = wp})
    end
    m:complete()
    return true, "completed"
end

function ScriptingEngine:setVar(name, value)
    self.variables[name] = value
end

function ScriptingEngine:getVar(name)
    return self.variables[name]
end

function ScriptingEngine:missionCount()
    local count = 0
    for _ in pairs(self.missions) do count = count + 1 end
    return count
end

-- 공개 API
return {
    ScriptingEngine = ScriptingEngine,
    Mission = Mission,
    EventBus = EventBus,
    EventTypes = EventTypes,
}
