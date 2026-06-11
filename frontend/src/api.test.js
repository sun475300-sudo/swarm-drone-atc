import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { listScenarios, getSnapshot, runScenario, setSession } from "./api.js";

// localStorage 스텁 (node 환경에는 없음).
const store = {};
globalThis.localStorage = {
  getItem: (k) => store[k] ?? null,
  setItem: (k, v) => {
    store[k] = String(v);
  },
  removeItem: (k) => {
    delete store[k];
  },
};

function mockFetch(payload, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => payload,
  });
}

beforeEach(() => {
  for (const k of Object.keys(store)) delete store[k];
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("listScenarios", () => {
  it("flattens the {id: meta} catalog into an array with id", async () => {
    globalThis.fetch = mockFetch({
      success: true,
      data: { high_density: { title: "고밀도" }, urban: { title: "도심" } },
    });
    const result = await listScenarios();
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ id: "high_density", title: "고밀도" });
  });

  it("returns empty array when catalog is missing", async () => {
    globalThis.fetch = mockFetch({ success: true });
    expect(await listScenarios()).toEqual([]);
  });
});

describe("getSnapshot", () => {
  it("returns the data envelope payload", async () => {
    globalThis.fetch = mockFetch({
      success: true,
      data: { t: 1, drones: [{ id: "d1" }], conflicts: [] },
    });
    const snap = await getSnapshot();
    expect(snap.drones).toHaveLength(1);
    expect(snap.conflicts).toEqual([]);
  });
});

describe("runScenario", () => {
  it("sends the bearer token and returns run metadata", async () => {
    setSession("tok123", "operator");
    const fetchMock = mockFetch({
      success: true,
      data: { run_id: "abc", status: "queued", mode: "scenario" },
    });
    globalThis.fetch = fetchMock;

    const run = await runScenario("urban", { seed: 7 });

    expect(run.run_id).toBe("abc");
    const [, opts] = fetchMock.mock.calls[0];
    expect(opts.headers.Authorization).toBe("Bearer tok123");
    // method 는 백엔드 RunScenarioBody 패턴(orca|apf|cbs|hybrid) 기본값 hybrid 로 전송.
    expect(JSON.parse(opts.body)).toEqual({ seed: 7, method: "hybrid" });
  });
});

describe("request error handling", () => {
  it("throws with the detail message on non-ok responses", async () => {
    globalThis.fetch = mockFetch({ detail: "invalid credentials" }, false, 401);
    await expect(getSnapshot()).rejects.toThrow("invalid credentials");
  });
});
