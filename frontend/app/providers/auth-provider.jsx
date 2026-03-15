"use client";

import { useCallback, useState, useEffect } from "react";

import { AuthContext } from "@/app/lib/auth/auth-context";

const apiBase = () => {
  const url = process.env.NEXT_PUBLIC_API_URL;
  return url ? url.replace(/\/$/, "") : "";
};

const JWT_STORAGE_KEY = "meetnote_jwt";

const buildStructuredError = (res, data, fallbackMessage) => {
  if (!res) {
    return {
      status: null,
      code: "network_error",
      message: fallbackMessage,
    };
  }

  const baseMessage =
    (data && typeof data.detail === "string" && data.detail.trim() !== ""
      ? data.detail
      : null) || fallbackMessage;

  let code = "api_error";
  if (res.status === 429) code = "rate_limit_exceeded";
  if (res.status === 401 || res.status === 403) code = "unauthorized";

  return {
    status: res.status,
    code,
    message: baseMessage,
  };
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [jwt, setJwt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [restoringAuth, setRestoringAuth] = useState(true);

  const fetchMe = useCallback(async (token, retries = 2) => {
    const base = apiBase();
    if (!base) return null;

    for (let i = 0; i <= retries; i++) {
      try {
        const res = await fetch(`${base}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: AbortSignal.timeout(5000),
        });

        if (res.ok) {
          return await res.json();
        }

        if (res.status === 401 || res.status === 403) {
          return null;
        }

        if (i < retries) {
          await new Promise((resolve) => setTimeout(resolve, 1000 * (i + 1)));
          continue;
        }

        return null;
      } catch (err) {
        if (
          i < retries &&
          (err.name === "TimeoutError" || err.name === "AbortError")
        ) {
          await new Promise((resolve) => setTimeout(resolve, 1000 * (i + 1)));
          continue;
        }
        return null;
      }
    }
    return null;
  }, []);

  const refreshAccessToken = useCallback(async () => {
    const base = apiBase();
    if (!base) return null;
    try {
      const res = await fetch(`${base}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        return null;
      }
      const data = await res.json();
      const token = data && data.access_token;
      if (!token) {
        return null;
      }
      localStorage.setItem(JWT_STORAGE_KEY, token);
      setJwt(token);
      return token;
    } catch {
      return null;
    }
  }, []);

  const login = useCallback(
    async (email, password) => {
      setLoading(true);
      setError(null);
      const base = apiBase();
      if (!base) {
        const structuredError = {
          status: null,
          code: "network_error",
          message: "API URL not configured",
        };
        setError(structuredError.message);
        setLoading(false);
        return { ok: false, error: structuredError };
      }
      try {
        const res = await fetch(`${base}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ email, password }),
        });
        let data = null;
        try {
          data = await res.json();
        } catch {
          data = null;
        }
        if (!res.ok) {
          const structuredError = buildStructuredError(
            res,
            data,
            "Login failed",
          );
          setError(structuredError.message);
          setLoading(false);
          return { ok: false, error: structuredError };
        }
        const token = data.access_token;
        if (!token) {
          const structuredError = {
            status: res.status,
            code: "api_error",
            message: "No token in response",
          };
          setError(structuredError.message);
          setLoading(false);
          return { ok: false, error: structuredError };
        }
        localStorage.setItem(JWT_STORAGE_KEY, token);
        setJwt(token);
        const me = await fetchMe(token);
        setUser(me);
        setError(null);
        setLoading(false);
        return { ok: true, error: null };
      } catch (err) {
        const structuredError = {
          status: null,
          code: "network_error",
          message: err.message || "Login failed",
        };
        setError(structuredError.message);
        setLoading(false);
        return { ok: false, error: structuredError };
      }
    },
    [fetchMe],
  );

  const register = useCallback(
    async (email, password, name = null) => {
      setLoading(true);
      setError(null);
      const base = apiBase();
      if (!base) {
        const structuredError = {
          status: null,
          code: "network_error",
          message: "API URL not configured",
        };
        setError(structuredError.message);
        setLoading(false);
        return { ok: false, error: structuredError };
      }
      try {
        const trimmedName =
          name != null && String(name).trim() !== ""
            ? String(name).trim()
            : null;
        const body = trimmedName
          ? { email, password, name: trimmedName }
          : { email, password };
        const res = await fetch(`${base}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        let data = null;
        try {
          data = await res.json();
        } catch {
          data = null;
        }
        if (!res.ok) {
          const structuredError = buildStructuredError(
            res,
            data,
            "Registration failed",
          );
          setError(structuredError.message);
          setLoading(false);
          return { ok: false, error: structuredError };
        }
        setLoading(false);
        return login(email, password);
      } catch (err) {
        const structuredError = {
          status: null,
          code: "network_error",
          message: err.message || "Registration failed",
        };
        setError(structuredError.message);
        setLoading(false);
        return { ok: false, error: structuredError };
      }
    },
    [login],
  );

  const logout = useCallback(async () => {
    const base = apiBase();
    if (base) {
      try {
        await fetch(`${base}/auth/logout`, {
          method: "POST",
          credentials: "include",
        });
      } catch {}
    }
    localStorage.removeItem(JWT_STORAGE_KEY);
    setUser(null);
    setJwt(null);
    setError(null);
    if (typeof window !== "undefined") {
      window.location.href = "/";
    }
  }, []);

  useEffect(() => {
    const restoreSession = async () => {
      const storedToken = localStorage.getItem(JWT_STORAGE_KEY);

      if (!storedToken) {
        setLoading(false);
        setRestoringAuth(false);
        return;
      }

      setJwt(storedToken);
      setLoading(true);
      setRestoringAuth(true);

      try {
        let me = await fetchMe(storedToken);

        if (!me) {
          const refreshed = await refreshAccessToken();
          if (refreshed) {
            me = await fetchMe(refreshed);
          }
        }

        if (me) {
          setUser(me);
          setError(null);
        } else {
          localStorage.removeItem(JWT_STORAGE_KEY);
          setJwt(null);
          setUser(null);
          setError("Session expired");
        }
      } catch (err) {
        console.error("Auth restoration error:", err);
        localStorage.removeItem(JWT_STORAGE_KEY);
        setJwt(null);
        setUser(null);
        setError("Failed to restore session");
      } finally {
        setLoading(false);
        setRestoringAuth(false);
      }
    };

    restoreSession();
  }, [fetchMe, refreshAccessToken]);

  const value = {
    user,
    jwt,
    loading,
    restoringAuth,
    error,
    setError,
    login,
    register,
    logout,
    refreshAccessToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthProvider;
