import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StatusBar } from "../components/StatusBar.jsx";

describe("StatusBar", () => {
  it("shows drone count", () => {
    render(<StatusBar droneCount={10} conflictCount={0} connected={true} onLogout={() => {}} />);
    expect(screen.getByText("드론 10기")).toBeInTheDocument();
  });

  it("shows conflict count", () => {
    render(<StatusBar droneCount={5} conflictCount={3} connected={true} onLogout={() => {}} />);
    expect(screen.getByText("충돌 3건")).toBeInTheDocument();
  });

  it("shows connected status", () => {
    render(<StatusBar droneCount={0} conflictCount={0} connected={true} onLogout={() => {}} />);
    expect(screen.getByText("연결됨")).toBeInTheDocument();
  });

  it("shows disconnected status", () => {
    render(<StatusBar droneCount={0} conflictCount={0} connected={false} onLogout={() => {}} />);
    expect(screen.getByText("연결 끊김")).toBeInTheDocument();
  });

  it("calls onLogout when button clicked", () => {
    const onLogout = vi.fn();
    render(<StatusBar droneCount={0} conflictCount={0} connected={true} onLogout={onLogout} />);
    fireEvent.click(screen.getByText("로그아웃"));
    expect(onLogout).toHaveBeenCalledOnce();
  });
});
