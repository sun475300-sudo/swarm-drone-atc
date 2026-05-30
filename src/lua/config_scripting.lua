-- Phase 635 — Lua Config Scripting Engine for SDACS
local config = {}

function config.load(path)
    local file = io.open(path, "r")
    if not file then return {} end
    local content = file:read("*all")
    file:close()
    local fn = load("return " .. content)
    return fn and fn() or {}
end

function config.get(cfg, key, default)
    local keys = {}
    for k in string.gmatch(key, "[^.]+") do keys[#keys+1] = k end
    local val = cfg
    for _, k in ipairs(keys) do
        if type(val) ~= "table" then return default end
        val = val[k]
    end
    return val ~= nil and val or default
end

return config
