"use client";

import { createContext, useCallback, useState, useEffect } from "react";

const apiBase = () => {
  const url = process.env.NEXT_PUBLIC_API_URL;
  return url ? url.replace(/\/$/, "") : "";
};

const JWT_STORAGE_KEY = "meetnote_jwt";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
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
          await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
          continue;
        }
        
        return null;
      } catch (err) {
        if (i < retries && (err.name === 'TimeoutError' || err.name === 'AbortError')) {
          await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
          continue;
        }
        return null;
      }
    }
    return null;
  }, []);

  const login = useCallback(
    async (email, password) => {
      setLoading(true);
      setError(null);
      const base = apiBase();
      if (!base) {
        setError("API URL not configured");
        setLoading(false);
        return false;
      }
      try {
        const res = await fetch(`${base}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (!res.ok) {
          setError(data.detail || "Login failed");
          setLoading(false);
          return false;
        }
        const token = data.access_token;
        if (!token) {
          setError("No token in response");
          setLoading(false);
          return false;
        }
        localStorage.setItem(JWT_STORAGE_KEY, token);
        setJwt(token);
        const me = await fetchMe(token);
        setUser(me);
        setError(null);
        setLoading(false);
        return true;
      } catch (err) {
        setError(err.message || "Login failed");
        setLoading(false);
        return false;
      }
    },
    [fetchMe]
  );

  const register = useCallback(
    async (email, password) => {
      setLoading(true);
      setError(null);
      const base = apiBase();
      if (!base) {
        setError("API URL not configured");
        setLoading(false);
        return false;
      }
      try {
        const res = await fetch(`${base}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (!res.ok) {
          setError(data.detail || "Registration failed");
          setLoading(false);
          return false;
        }
        setLoading(false);
        return login(email, password);
      } catch (err) {
        setError(err.message || "Registration failed");
        setLoading(false);
        return false;
      }
    },
    [login]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(JWT_STORAGE_KEY);
    setUser(null);
    setJwt(null);
    setError(null);
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
        const me = await fetchMe(storedToken);
        
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
  }, [fetchMe]);

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
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export default AuthProvider;
