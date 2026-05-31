import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DroneTable } from "../components/DroneTable.jsx";

const makeDrone = (id, lat = 37.5, lon = 127.0, alt = 50) => ({ id, lat, lon, alt });

describe("DroneTable", () => {
  it("shows empty state when no drones", () => {
    render(<DroneTable drones={[]} conflicts={[]} />);
    expect(screen.getByText("드론 데이터 없음")).toBeInTheDocument();
  });

  it("renders drone rows", () => {
    const drones = [makeDrone("d1"), makeDrone("d2")];
    render(<DroneTable drones={drones} conflicts={[]} />);
    expect(screen.getByText("d1")).toBeInTheDocument();
    expect(screen.getByText("d2")).toBeInTheDocument();
  });

  it("marks conflicted drones with warning label", () => {
    const drones = [makeDrone("d1"), makeDrone("d2")];
    const conflicts = [{ drone_a: "d1", drone_b: "d2" }];
    render(<DroneTable drones={drones} conflicts={conflicts} />);
    const warnings = screen.getAllByText("⚠ 충돌위험");
    expect(warnings.length).toBe(2);
  });

  it("shows 정상 for drones without conflicts", () => {
    const drones = [makeDrone("d1"), makeDrone("d2")];
    const conflicts = [{ drone_a: "d1", drone_b: "d2" }];
    const allDrones = [...drones, makeDrone("d3")];
    render(<DroneTable drones={allDrones} conflicts={conflicts} />);
    expect(screen.getByText("정상")).toBeInTheDocument();
  });

  it("displays altitude with one decimal", () => {
    render(<DroneTable drones={[makeDrone("d1", 37.5, 127.0, 123.456)]} conflicts={[]} />);
    expect(screen.getByText("123.5")).toBeInTheDocument();
  });

  it("displays dash for missing coordinates", () => {
    const drone = { id: "d1", lat: undefined, lon: undefined, alt: undefined };
    render(<DroneTable drones={[drone]} conflicts={[]} />);
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(3);
  });
});
