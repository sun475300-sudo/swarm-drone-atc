-- Phase 635: Config Scripting — Lua
-- SDACS Lua-based configuration scripting for drone fleet parameters

local Config = {}
Config.__index = Config

function Config.new(defaults)
    local self = setmetatable({}, Config)
    self._store   = {}
    self._defaults = defaults or {}
    self._validators = {}
    for k, v in pairs(self._defaults) do self._store[k] = v end
    return self
end

function Config:set(key, value)
    local validator = self._validators[key]
    if validator and not validator(value) then
        error("Invalid value for key: " .. key)
    end
    self._store[key] = value
end

function Config:get(key, default)
    return self._store[key] ~= nil and self._store[key] or default
end

function Config:validate(key, fn)
    self._validators[key] = fn
end

function Config:load_string(str)
    local fn = load("return {" .. str .. "}")
    if not fn then return false end
    local ok, data = pcall(fn)
    if ok and type(data) == "table" then
        for k, v in pairs(data) do self:set(k, v) end
        return true
    end
    return false
end

function Config:all()
    return self._store
end

-- Demo
local cfg = Config.new({
    drone_count   = 10,
    max_altitude  = 120,
    default_speed = 10,
})
cfg:validate("drone_count", function(v) return type(v)=="number" and v > 0 end)
cfg:set("drone_count", 15)
print("Phase 635: drone_count=" .. cfg:get("drone_count"))
print("max_altitude=" .. cfg:get("max_altitude"))
