import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LoginForm } from "../components/LoginForm.jsx";

describe("LoginForm", () => {
  it("renders login form elements", () => {
    render(<LoginForm onLogin={() => {}} error={null} loading={false} />);
    expect(screen.getByText("SDACS")).toBeInTheDocument();
    expect(screen.getByLabelText("사용자명") ?? screen.getAllByRole("textbox")[0]).toBeTruthy();
    expect(screen.getByText("로그인")).toBeInTheDocument();
  });

  it("shows error message when error prop provided", () => {
    render(<LoginForm onLogin={() => {}} error="Login failed" loading={false} />);
    expect(screen.getByText("Login failed")).toBeInTheDocument();
  });

  it("shows loading state on button", () => {
    render(<LoginForm onLogin={() => {}} error={null} loading={true} />);
    expect(screen.getByText("로그인 중…")).toBeInTheDocument();
  });

  it("calls onLogin with username and password on submit", () => {
    const onLogin = vi.fn();
    render(<LoginForm onLogin={onLogin} error={null} loading={false} />);
    const inputs = screen.getAllByRole("textbox");
    fireEvent.change(inputs[0], { target: { value: "admin" } });

    const passwordInput = document.querySelector('input[type="password"]');
    fireEvent.change(passwordInput, { target: { value: "secret" } });

    fireEvent.click(screen.getByText("로그인"));
    expect(onLogin).toHaveBeenCalledWith("admin", "secret");
  });
});
