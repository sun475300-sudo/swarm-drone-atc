-- SDACS Config Scripting — Lua
-- 드론 군집 시뮬레이션 설정 스크립팅 엔진

local Config = {}
Config.__index = Config

-- 기본 설정값
local DEFAULTS = {
    simulation = {
        duration = 60,
        time_step = 0.1,
        seed = 42,
    },
    drones = {
        default_count = 50,
        separation_min = 30.0,
        separation_warn = 50.0,
        max_speed = 15.0,
        max_altitude = 400.0,
    },
    control = {
        apf_k_att = 1.0,
        apf_k_rep = 500.0,
        apf_rho0 = 50.0,
        update_hz = 10,
    },
    analytics = {
        enable = true,
        record_interval = 1.0,
        output_dir = "results/",
    },
}

function Config.new(overrides)
    local self = setmetatable({}, Config)
    self._data = Config._deep_copy(DEFAULTS)
    if overrides then
        Config._deep_merge(self._data, overrides)
    end
    return self
end

function Config._deep_copy(t)
    if type(t) ~= "table" then return t end
    local copy = {}
    for k, v in pairs(t) do
        copy[k] = Config._deep_copy(v)
    end
    return setmetatable(copy, getmetatable(t))
end

function Config._deep_merge(target, source)
    for k, v in pairs(source) do
        if type(v) == "table" and type(target[k]) == "table" then
            Config._deep_merge(target[k], v)
        else
            target[k] = v
        end
    end
end

function Config:get(path)
    local parts = {}
    for part in path:gmatch("[^%.]+") do
        parts[#parts + 1] = part
    end
    local cur = self._data
    for _, part in ipairs(parts) do
        if type(cur) ~= "table" then return nil end
        cur = cur[part]
    end
    return cur
end

function Config:set(path, value)
    local parts = {}
    for part in path:gmatch("[^%.]+") do
        parts[#parts + 1] = part
    end
    local cur = self._data
    for i = 1, #parts - 1 do
        local part = parts[i]
        if type(cur[part]) ~= "table" then
            cur[part] = {}
        end
        cur = cur[part]
    end
    cur[parts[#parts]] = value
end

function Config:validate()
    local errors = {}
    local count = self:get("drones.default_count")
    if not count or count < 1 or count > 10000 then
        errors[#errors + 1] = "drones.default_count must be 1-10000"
    end
    local dur = self:get("simulation.duration")
    if not dur or dur <= 0 then
        errors[#errors + 1] = "simulation.duration must be > 0"
    end
    local hz = self:get("control.update_hz")
    if not hz or hz < 1 or hz > 100 then
        errors[#errors + 1] = "control.update_hz must be 1-100"
    end
    return #errors == 0, errors
end

function Config:to_table()
    return Config._deep_copy(self._data)
end

function Config:__tostring()
    return string.format("Config{drones=%d, duration=%ds, hz=%dHz}",
        self:get("drones.default_count") or 0,
        self:get("simulation.duration") or 0,
        self:get("control.update_hz") or 0)
end

-- 시나리오 프리셋
local Scenarios = {
    high_density = Config.new({ drones = { default_count = 200 } }),
    wind_stress  = Config.new({ simulation = { duration = 120 } }),
    quick_test   = Config.new({ simulation = { duration = 10, seed = 1 } }),
}

return {
    Config = Config,
    Scenarios = Scenarios,
    defaults = DEFAULTS,
}
