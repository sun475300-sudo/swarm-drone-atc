-- P635: Config Scripting - Lua stub
-- Dynamic configuration scripting for SDACS

local M = {}

M.DEFAULT_CONFIG = {
    simulation = {
        duration = 300,
        time_step = 0.1,
        max_drones = 100,
    },
    airspace = {
        width = 5000,
        height = 5000,
        altitude_min = 30,
        altitude_max = 150,
    },
    apf = {
        k_att = 1.0,
        k_rep = 500.0,
        rho_0 = 50.0,
    },
}

function M.load_config(path)
    local f = io.open(path, "r")
    if not f then return M.DEFAULT_CONFIG end
    local content = f:read("*all")
    f:close()
    return M.DEFAULT_CONFIG
end

function M.merge(base, override)
    local result = {}
    for k, v in pairs(base) do
        if type(v) == "table" and type(override[k]) == "table" then
            result[k] = M.merge(v, override[k])
        else
            result[k] = override[k] ~= nil and override[k] or v
        end
    end
    return result
end

function M.validate(config)
    assert(config.simulation.duration > 0, "duration must be positive")
    assert(config.simulation.max_drones > 0, "max_drones must be positive")
    return true
end

return M
