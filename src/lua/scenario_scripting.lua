--[[
SDACS 시나리오 스크립팅 엔진 — Lua
====================================
경량 DSL로 시뮬레이션 시나리오 정의 + 실행

기능:
  - 이벤트 트리거 정의 (시간/조건 기반)
  - 드론 행동 스크립팅
  - 기상/장애 주입
  - 시나리오 매크로
  - 실시간 조건 평가
]]

-- ── 시나리오 엔진 ───────────────────────────────────────

local ScenarioEngine = {}
ScenarioEngine.__index = ScenarioEngine

function ScenarioEngine.new()
    local self = setmetatable({}, ScenarioEngine)
    self.events = {}          -- 시간 기반 이벤트
    self.conditions = {}      -- 조건 기반 트리거
    self.actions = {}         -- 실행된 액션 로그
    self.state = {            -- 시뮬레이션 상태
        t = 0,
        drones = {},
        weather = { wind_speed = 5, wind_dir = 0, visibility = 10000 },
        alerts = {},
        paused = false
    }
    self.macros = {}
    self.log = {}
    return self
end

-- 시간 기반 이벤트 등록
function ScenarioEngine:at(time_sec, action_fn, description)
    table.insert(self.events, {
        time = time_sec,
        action = action_fn,
        description = description or "unnamed",
        executed = false
    })
    -- 시간순 정렬
    table.sort(self.events, function(a, b) return a.time < b.time end)
    return self
end

-- 조건 기반 트리거 등록
function ScenarioEngine:when(condition_fn, action_fn, description, once)
    table.insert(self.conditions, {
        condition = condition_fn,
        action = action_fn,
        description = description or "unnamed",
        once = once ~= false,  -- 기본: 1회만
        executed = false
    })
    return self
end

-- 매크로 등록 (재사용 가능한 시나리오 블록)
function ScenarioEngine:macro(name, fn)
    self.macros[name] = fn
    return self
end

-- 매크로 실행
function ScenarioEngine:run_macro(name, ...)
    local fn = self.macros[name]
    if fn then fn(self, ...) end
    return self
end

-- ── 드론 제어 액션 ──────────────────────────────────────

function ScenarioEngine:spawn_drone(drone_id, x, y, z, drone_type)
    self.state.drones[drone_id] = {
        id = drone_id,
        x = x or 0, y = y or 0, z = z or 50,
        vx = 0, vy = 0, vz = 0,
        battery = 100,
        status = "ACTIVE",
        drone_type = drone_type or "DELIVERY"
    }
    self:_log("SPAWN", drone_id .. " at (" .. x .. "," .. y .. "," .. z .. ")")
    return self
end

function ScenarioEngine:move_drone(drone_id, target_x, target_y, target_z, speed)
    local drone = self.state.drones[drone_id]
    if not drone then return self end

    local dx = target_x - drone.x
    local dy = target_y - drone.y
    local dz = (target_z or drone.z) - drone.z
    local dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    local spd = speed or 10

    if dist > 0.1 then
        drone.vx = dx / dist * spd
        drone.vy = dy / dist * spd
        drone.vz = dz / dist * spd
    end

    self:_log("MOVE", drone_id .. " → (" .. target_x .. "," .. target_y .. ")")
    return self
end

function ScenarioEngine:set_drone_status(drone_id, status)
    local drone = self.state.drones[drone_id]
    if drone then
        drone.status = status
        self:_log("STATUS", drone_id .. " → " .. status)
    end
    return self
end

-- ── 환경 제어 ───────────────────────────────────────────

function ScenarioEngine:set_weather(wind_speed, wind_dir, visibility)
    self.state.weather.wind_speed = wind_speed or self.state.weather.wind_speed
    self.state.weather.wind_dir = wind_dir or self.state.weather.wind_dir
    self.state.weather.visibility = visibility or self.state.weather.visibility
    self:_log("WEATHER", string.format("wind=%.1f dir=%d vis=%d",
        self.state.weather.wind_speed, self.state.weather.wind_dir, self.state.weather.visibility))
    return self
end

function ScenarioEngine:inject_failure(drone_id, failure_type)
    local drone = self.state.drones[drone_id]
    if drone then
        drone.status = "FAULT"
        drone.failure = failure_type
        self:_log("FAILURE", drone_id .. " — " .. failure_type)
    end
    return self
end

function ScenarioEngine:add_nfz(nfz_id, cx, cy, radius, reason)
    self.state.nfz = self.state.nfz or {}
    self.state.nfz[nfz_id] = {
        id = nfz_id, cx = cx, cy = cy, radius = radius,
        reason = reason or "restricted"
    }
    self:_log("NFZ", nfz_id .. " at (" .. cx .. "," .. cy .. ") r=" .. radius)
    return self
end

-- ── 시뮬레이션 틱 ───────────────────────────────────────

function ScenarioEngine:tick(dt)
    if self.state.paused then return end

    self.state.t = self.state.t + dt

    -- 시간 기반 이벤트 실행
    for _, event in ipairs(self.events) do
        if not event.executed and self.state.t >= event.time then
            event.action(self)
            event.executed = true
            self:_log("EVENT", event.description .. " (t=" .. event.time .. ")")
        end
    end

    -- 조건 기반 트리거 평가
    for _, cond in ipairs(self.conditions) do
        if not cond.executed and cond.condition(self.state) then
            cond.action(self)
            if cond.once then cond.executed = true end
            self:_log("TRIGGER", cond.description)
        end
    end

    -- 드론 위치 업데이트
    for _, drone in pairs(self.state.drones) do
        if drone.status == "ACTIVE" then
            drone.x = drone.x + drone.vx * dt
            drone.y = drone.y + drone.vy * dt
            drone.z = drone.z + drone.vz * dt
            drone.battery = math.max(0, drone.battery - 0.01 * dt)
        end
    end
end

-- 전체 시나리오 실행
function ScenarioEngine:run(duration, dt)
    dt = dt or 1.0
    local steps = math.floor(duration / dt)
    for _ = 1, steps do
        self:tick(dt)
    end
    return self
end

-- ── 유틸리티 ────────────────────────────────────────────

function ScenarioEngine:_log(category, message)
    table.insert(self.log, {
        t = self.state.t,
        category = category,
        message = message
    })
end

function ScenarioEngine:drone_count()
    local count = 0
    for _ in pairs(self.state.drones) do count = count + 1 end
    return count
end

function ScenarioEngine:active_drones()
    local count = 0
    for _, d in pairs(self.state.drones) do
        if d.status == "ACTIVE" then count = count + 1 end
    end
    return count
end

function ScenarioEngine:summary()
    return {
        time = self.state.t,
        drones = self:drone_count(),
        active = self:active_drones(),
        events_total = #self.events,
        events_executed = #(function()
            local e = {}
            for _, ev in ipairs(self.events) do
                if ev.executed then table.insert(e, ev) end
            end
            return e
        end)(),
        log_entries = #self.log,
        weather = self.state.weather
    }
end

-- ── 사전 정의 시나리오 매크로 ───────────────────────────

-- 고밀도 시나리오
ScenarioEngine.PRESETS = {}

ScenarioEngine.PRESETS.high_density = function(engine, n_drones)
    n_drones = n_drones or 100
    for i = 1, n_drones do
        local x = math.random() * 1000
        local y = math.random() * 1000
        engine:spawn_drone("d" .. i, x, y, 50 + math.random() * 70, "DELIVERY")
    end
end

ScenarioEngine.PRESETS.weather_emergency = function(engine)
    engine:at(30, function(e)
        e:set_weather(20, 270, 2000)
    end, "강풍 시작")
    engine:at(60, function(e)
        e:set_weather(25, 270, 500)
    end, "폭풍 도달")
    engine:at(120, function(e)
        e:set_weather(5, 180, 10000)
    end, "기상 회복")
end

ScenarioEngine.PRESETS.gps_spoofing = function(engine, target_drone)
    target_drone = target_drone or "d1"
    engine:at(45, function(e)
        e:inject_failure(target_drone, "GPS_SPOOFING")
    end, "GPS 스푸핑 공격")
end

return ScenarioEngine
