-- SDACS configuration scripting layer — Lua stub
local M = {}

M.defaults = {
    drones = 10,
    separation_m = 50,
    max_speed_mps = 15,
    simulation_hz = 10,
}

function M.load(path)
    -- Placeholder: load YAML/JSON config from path
    return M.defaults
end

function M.validate(cfg)
    assert(cfg.drones > 0, "drones must be positive")
    assert(cfg.separation_m > 0, "separation must be positive")
    return true
end

return M
