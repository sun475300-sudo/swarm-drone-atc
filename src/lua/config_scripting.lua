-- Config Scripting Engine — SDACS Phase 635
local Config = {}
Config.__index = Config

function Config.new()
  return setmetatable({data = {}}, Config)
end

function Config:set(key, value)
  self.data[key] = value
end

function Config:get(key)
  return self.data[key]
end

return Config
