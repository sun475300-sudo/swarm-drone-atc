import { useState } from "react";
import { login as apiLogin } from "../api/client.js";

const TOKEN_KEY = "sdacs_token";

export function useAuth() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY));
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function login(username, password) {
    setLoading(true);
    setError(null);
    try {
      const data = await apiLogin(username, password);
      sessionStorage.setItem(TOKEN_KEY, data.access_token);
      setToken(data.access_token);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null);
  }

  return { token, login, logout, error, loading };
}
