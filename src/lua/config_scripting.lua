-- Phase 635 — Swarm Config Scripting Engine in Lua
local M = {}

M.defaults = {
  max_drones = 500,
  min_separation_m = 30.0,
  collision_lookahead_s = 90.0,
  telemetry_hz = 10.0,
  apf_repulsion_k = 1000.0,
}

function M.load(path)
  local f = loadfile(path)
  if not f then return M.defaults end
  local env = {}
  setfenv(f, env)
  f()
  return setmetatable(env, {__index = M.defaults})
end

function M.validate(cfg)
  assert(cfg.max_drones > 0, "max_drones must be positive")
  assert(cfg.min_separation_m > 0, "min_separation_m must be positive")
  return true
end

return M
