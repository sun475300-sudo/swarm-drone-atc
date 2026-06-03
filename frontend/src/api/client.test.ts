import { describe, expect, it } from "vitest";
import { ApiError, telemetryWsUrl, unwrap } from "./client";

describe("unwrap", () => {
  it("returns data when envelope succeeds", () => {
    const result = unwrap({ success: true, data: { foo: 1 } }, 200);
    expect(result).toEqual({ foo: 1 });
  });

  it("throws ApiError with server error message on failure", () => {
    expect(() => unwrap({ success: false, error: "boom" }, 500)).toThrowError(
      ApiError,
    );
    try {
      unwrap({ success: false, error: "boom" }, 500);
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(500);
      expect((err as ApiError).message).toBe("boom");
    }
  });

  it("throws when success is true but data is missing", () => {
    expect(() => unwrap({ success: true }, 200)).toThrowError(ApiError);
  });
});

describe("telemetryWsUrl", () => {
  it("converts the http API base to a ws telemetry url", () => {
    // 기본 베이스(http://localhost:8000) → ws://localhost:8000/ws/telemetry
    expect(telemetryWsUrl()).toBe("ws://localhost:8000/ws/telemetry");
  });
});
