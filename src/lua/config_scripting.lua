-- config_scripting.lua - Lua configuration scripting for SDACS
-- Dynamic configuration and scripting engine

local Config = {}
Config.__index = Config

function Config.new(defaults)
    local self = setmetatable({}, Config)
    self._store = {}
    self._validators = {}
    if defaults then
        for k, v in pairs(defaults) do
            self._store[k] = v
        end
    end
    return self
end

function Config:set(key, value)
    if self._validators[key] then
        local ok, err = self._validators[key](value)
        if not ok then error("Validation failed for " .. key .. ": " .. (err or "")) end
    end
    self._store[key] = value
end

function Config:get(key, default)
    return self._store[key] or default
end

function Config:validate_number(min, max)
    return function(v)
        if type(v) ~= "number" then return false, "must be number" end
        if min and v < min then return false, "below minimum " .. min end
        if max and v > max then return false, "above maximum " .. max end
        return true
    end
end

-- Default SDACS configuration
local sdacs_config = Config.new({
    ["simulation.duration"]    = 60,
    ["simulation.drone_count"] = 10,
    ["wind.base_speed"]        = 5.0,
    ["apf.k_att"]              = 1.0,
    ["apf.k_rep"]              = 100.0,
    ["api.port"]               = 8080,
})

print("SDACS Config Scripting Engine loaded")
print("Drone count: " .. tostring(sdacs_config:get("simulation.drone_count")))
return sdacs_config
