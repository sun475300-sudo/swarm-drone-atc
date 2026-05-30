-- Phase 553: swarm_scripting_engine — Lua 기반 군집 드론 스크립팅 엔진
-- SDACS Mission Scripting Engine

local SwarmScriptingEngine = {}
SwarmScriptingEngine.__index = SwarmScriptingEngine

-- 이벤트 타입 정의
local EventType = {
  MISSION_START    = "mission_start",
  MISSION_COMPLETE = "mission_complete",
  WAYPOINT_REACHED = "waypoint_reached",
  CONFLICT_ALERT   = "conflict_alert",
  BATTERY_LOW      = "battery_low",
  GEOFENCE_BREACH  = "geofence_breach",
  DRONE_LANDED     = "drone_landed",
  EMERGENCY_STOP   = "emergency_stop",
}

-- Mission 상태 정의
local MissionStatus = {
  IDLE     = "IDLE",
  RUNNING  = "RUNNING",
  PAUSED   = "PAUSED",
  COMPLETE = "COMPLETE",
  ABORTED  = "ABORTED",
}

-- 이벤트 리스너 등록
function SwarmScriptingEngine:on(event_type, callback)
  if not self.listeners[event_type] then
    self.listeners[event_type] = {}
  end
  table.insert(self.listeners[event_type], callback)
end

-- 이벤트 발행
function SwarmScriptingEngine:emit(event_type, data)
  local handlers = self.listeners[event_type] or {}
  for _, handler in ipairs(handlers) do
    local ok, err = pcall(handler, data)
    if not ok then
      print(string.format("[ScriptEngine] Event handler error for %s: %s", event_type, err))
    end
  end
end

-- Mission 웨이포인트 구조체
local function Waypoint(lat, lon, alt, speed, hold_time)
  return {
    lat       = lat or 0.0,
    lon       = lon or 0.0,
    alt       = alt or 30.0,
    speed     = speed or 5.0,
    hold_time = hold_time or 0,
    reached   = false,
  }
end

-- Mission 스크립트 정의
local function Mission(name, drone_ids)
  return {
    name       = name,
    drone_ids  = drone_ids or {},
    waypoints  = {},
    status     = MissionStatus.IDLE,
    start_time = nil,
    end_time   = nil,
    actions    = {},
  }
end

-- Mission 웨이포인트 추가
function SwarmScriptingEngine:addWaypoint(mission, lat, lon, alt, speed)
  table.insert(mission.waypoints, Waypoint(lat, lon, alt, speed))
end

-- Mission 시작
function SwarmScriptingEngine:startMission(mission)
  if mission.status ~= MissionStatus.IDLE then
    print("[ScriptEngine] Cannot start mission: status=" .. mission.status)
    return false
  end
  mission.status     = MissionStatus.RUNNING
  mission.start_time = os.time()
  self:emit(EventType.MISSION_START, { mission = mission })
  print(string.format("[ScriptEngine] Mission '%s' started with %d drones",
    mission.name, #mission.drone_ids))
  return true
end

-- 웨이포인트 도달 처리
function SwarmScriptingEngine:onWaypointReached(mission, wp_index)
  local wp = mission.waypoints[wp_index]
  if not wp then return end
  wp.reached = true
  self:emit(EventType.WAYPOINT_REACHED, {
    mission  = mission,
    wp_index = wp_index,
    waypoint = wp,
  })
  -- 모든 웨이포인트 도달 확인
  local all_reached = true
  for _, w in ipairs(mission.waypoints) do
    if not w.reached then
      all_reached = false
      break
    end
  end
  if all_reached then
    self:completeMission(mission)
  end
end

-- Mission 완료
function SwarmScriptingEngine:completeMission(mission)
  mission.status   = MissionStatus.COMPLETE
  mission.end_time = os.time()
  self:emit(EventType.MISSION_COMPLETE, { mission = mission })
  local duration = mission.end_time - mission.start_time
  print(string.format("[ScriptEngine] Mission '%s' complete in %ds", mission.name, duration))
end

-- Mission 중단
function SwarmScriptingEngine:abortMission(mission, reason)
  mission.status = MissionStatus.ABORTED
  self:emit(EventType.EMERGENCY_STOP, { mission = mission, reason = reason })
  print(string.format("[ScriptEngine] Mission '%s' ABORTED: %s", mission.name, reason))
end

-- 스크립팅 엔진 생성자
function SwarmScriptingEngine.new()
  local self = setmetatable({}, SwarmScriptingEngine)
  self.listeners  = {}
  self.missions   = {}
  self.variables  = {}
  return self
end

-- 변수 설정 (스크립트 공유 상태)
function SwarmScriptingEngine:setVar(key, value)
  self.variables[key] = value
end

-- 변수 읽기
function SwarmScriptingEngine:getVar(key, default)
  return self.variables[key] or default
end

-- 스크립팅 엔진 초기화 예시
local function main()
  print("SDACS Swarm Scripting Engine — Phase 553")
  local engine = SwarmScriptingEngine.new()

  -- 이벤트 핸들러 등록
  engine:on(EventType.MISSION_START, function(data)
    print("Event: mission started — " .. data.mission.name)
  end)
  engine:on(EventType.MISSION_COMPLETE, function(data)
    print("Event: mission complete — " .. data.mission.name)
  end)
  engine:on(EventType.WAYPOINT_REACHED, function(data)
    print("Event: waypoint " .. data.wp_index .. " reached")
  end)

  -- Mission 생성 및 실행
  local m = Mission("patrol_route", {0, 1, 2})
  engine:addWaypoint(m, 37.50, 127.00, 50.0, 5.0)
  engine:addWaypoint(m, 37.51, 127.01, 60.0, 5.0)
  engine:addWaypoint(m, 37.52, 127.02, 50.0, 5.0)

  engine:startMission(m)
  engine:onWaypointReached(m, 1)
  engine:onWaypointReached(m, 2)
  engine:onWaypointReached(m, 3)
end

main()
return SwarmScriptingEngine
