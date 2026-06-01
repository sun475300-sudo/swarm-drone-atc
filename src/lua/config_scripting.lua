-- Phase 635 — Lua Config Scripting Engine for SDACS
-- Dynamic configuration loader and validator

local M = {}

--- Default simulation configuration
M.defaults = {
    drones = { default_count = 20, max_count = 500 },
    simulation = { duration_s = 300, dt = 0.1, seed = 42 },
    airspace = { width_m = 2000, height_m = 2000, alt_max_m = 400 },
}

--- Load and merge config from a table, applying defaults for missing keys.
-- @param user_cfg table  Partial user config (may be nil)
-- @return table  Merged config with defaults filled in
function M.load(user_cfg)
    local cfg = {}
    for section, defaults in pairs(M.defaults) do
        cfg[section] = {}
        for key, default_val in pairs(defaults) do
            if user_cfg and user_cfg[section] and user_cfg[section][key] ~= nil then
                cfg[section][key] = user_cfg[section][key]
            else
                cfg[section][key] = default_val
            end
        end
    end
    return cfg
end

--- Validate that a config table has required numeric fields within bounds.
-- @param cfg table  Config to validate
-- @return boolean, string  (valid, error_message_or_nil)
function M.validate(cfg)
    if not cfg.drones or cfg.drones.default_count < 1 then
        return false, "drones.default_count must be >= 1"
    end
    if not cfg.simulation or cfg.simulation.dt <= 0 then
        return false, "simulation.dt must be > 0"
    end
    return true, nil
end

return M
