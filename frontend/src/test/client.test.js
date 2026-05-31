import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  connectTelemetry,
  fetchScenarios,
  fetchSnapshot,
  login,
  runScenario,
} from "../api/client.js";

const mockFetch = (data, ok = true, status = 200) => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => data,
  });
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("login", () => {
  it("POSTs credentials and returns token", async () => {
    mockFetch({ access_token: "tok123", token_type: "bearer" });
    const result = await login("admin", "pass");
    expect(result.access_token).toBe("tok123");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/auth/token",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch({}, false, 401);
    await expect(login("bad", "creds")).rejects.toThrow("Login failed");
  });
});

describe("fetchSnapshot", () => {
  it("GETs snapshot with auth header", async () => {
    mockFetch({ drones: [], conflicts: [] });
    await fetchSnapshot("mytoken");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/airspace/snapshot",
      expect.objectContaining({ headers: { Authorization: "Bearer mytoken" } })
    );
  });
});

describe("fetchScenarios", () => {
  it("returns scenario list", async () => {
    mockFetch([{ id: "s1", name: "High Density" }]);
    const result = await fetchScenarios("tok");
    expect(result[0].id).toBe("s1");
  });
});

describe("runScenario", () => {
  it("POSTs to correct URL", async () => {
    mockFetch({ run_id: "r123" });
    const result = await runScenario("tok", "scenario_1");
    expect(result.run_id).toBe("r123");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/scenarios/scenario_1/run",
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("connectTelemetry", () => {
  beforeEach(() => {
    globalThis.WebSocket = vi.fn(() => ({
      onmessage: null,
      onopen: null,
      onclose: null,
      onerror: null,
      close: vi.fn(),
    }));
    delete globalThis.window;
    globalThis.window = { location: { href: "http://localhost:3000/" } };
  });

  it("creates WebSocket with token in query param", () => {
    connectTelemetry("mytoken", () => {});
    expect(globalThis.WebSocket).toHaveBeenCalledWith(
      expect.stringContaining("token=mytoken")
    );
  });

  it("calls onMessage with parsed JSON on message", () => {
    const ws = { onmessage: null, onopen: null, onclose: null, onerror: null, close: vi.fn() };
    globalThis.WebSocket = vi.fn(() => ws);
    const onMessage = vi.fn();
    connectTelemetry("tok", onMessage);
    ws.onmessage({ data: JSON.stringify({ drones: [{ id: "d1" }] }) });
    expect(onMessage).toHaveBeenCalledWith({ drones: [{ id: "d1" }] });
  });
});
