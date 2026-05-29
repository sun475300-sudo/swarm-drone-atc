-- Phase 635: Config Scripting — Lua Embedded Configuration Engine
-- 임베디드 설정 스크립트 엔진 (드론 FW)

local ConfigEngine = {}
ConfigEngine.__index = ConfigEngine

function ConfigEngine.new()
    local self = setmetatable({}, ConfigEngine)
    self.params = {}
    self.defaults = {
        max_altitude = 120.0,
        min_separation = 50.0,
        max_speed = 15.0,
        battery_threshold = 0.15,
        heartbeat_interval = 1.0,
        geofence_radius = 500.0,
        wind_compensation = true,
        formation_type = "V",
        communication_freq = 1.0,
        emergency_protocol = "RTL",
    }
    self.validators = {}
    self.history = {}
    return self
end

function ConfigEngine:set(key, value)
    if self.validators[key] then
        local ok, err = self.validators[key](value)
        if not ok then
            return false, "Validation failed: " .. (err or "unknown")
        end
    end
    local old = self.params[key]
    self.params[key] = value
    table.insert(self.history, {
        key = key,
        old_value = old,
        new_value = value,
        timestamp = os.time(),
    })
    return true
end

function ConfigEngine:get(key)
    if self.params[key] ~= nil then
        return self.params[key]
    end
    return self.defaults[key]
end

function ConfigEngine:add_validator(key, fn)
    self.validators[key] = fn
end

function ConfigEngine:load_profile(profile)
    for key, value in pairs(profile) do
        self:set(key, value)
    end
end

function ConfigEngine:export()
    local result = {}
    for key, default_val in pairs(self.defaults) do
        result[key] = self:get(key)
    end
    for key, val in pairs(self.params) do
        result[key] = val
    end
    return result
end

function ConfigEngine:get_history()
    return self.history
end

function ConfigEngine:reset()
    self.params = {}
    self.history = {}
end

-- Predefined profiles
local PROFILES = {
    normal = {
        max_altitude = 120.0,
        min_separation = 50.0,
        max_speed = 15.0,
    },
    high_density = {
        max_altitude = 80.0,
        min_separation = 30.0,
        max_speed = 10.0,
    },
    storm = {
        max_altitude = 50.0,
        min_separation = 80.0,
        max_speed = 8.0,
        wind_compensation = true,
    },
}

return {
    ConfigEngine = ConfigEngine,
    PROFILES = PROFILES,
}
