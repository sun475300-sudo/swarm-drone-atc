-- Phase 635 — Config Scripting (Lua)
-- SDACS 시뮬레이션 파라미터를 Lua 스크립트로 동적 설정

local M = {}

--- 기본 시뮬레이션 설정값
M.defaults = {
    n_drones        = 50,
    seed            = 42,
    duration_s      = 300,
    safe_sep_m      = 30.0,
    apf = {
        k_attr      = 1.0,
        k_rep       = 500.0,
        d_rep       = 40.0,
        max_speed   = 15.0,
    },
    wind = {
        enabled     = true,
        base_speed  = 5.0,
        gust_factor = 1.5,
    },
}

--- 시나리오별 오버라이드 테이블
M.scenarios = {
    high_density = {
        n_drones = 200,
        safe_sep_m = 20.0,
    },
    emergency = {
        n_drones = 30,
        duration_s = 60,
        wind = { enabled = false },
    },
    storm = {
        wind = {
            enabled = true,
            base_speed = 18.0,
            gust_factor = 3.0,
        },
    },
}

--- 설정을 병합한다. base 위에 override를 덮어쓴다.
function M.merge(base, override)
    local result = {}
    for k, v in pairs(base) do
        result[k] = type(v) == "table" and M.merge(v, {}) or v
    end
    for k, v in pairs(override) do
        if type(v) == "table" and type(result[k]) == "table" then
            result[k] = M.merge(result[k], v)
        else
            result[k] = v
        end
    end
    return result
end

--- 시나리오 설정을 반환한다.
function M.load(scenario_name)
    local override = M.scenarios[scenario_name] or {}
    return M.merge(M.defaults, override)
end

return M
