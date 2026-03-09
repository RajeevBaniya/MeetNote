"use client";

import { useState, useCallback } from "react";

import { useAuth } from "@/app/lib/auth/use-auth";
import PasswordField from "@/app/components/auth/password-field";

const LoginForm = ({ onSuccess, onSwitchMode, message }) => {
  const { login, loading, error, setError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      setError(null);
      const ok = await login(email.trim(), password);
      if (ok && typeof onSuccess === "function") {
        onSuccess();
      }
    },
    [email, password, onSuccess, login, setError],
  );

  const handleSwitchToSignup = useCallback(() => {
    if (typeof onSwitchMode === "function") onSwitchMode("signup");
    setError(null);
  }, [onSwitchMode, setError]);

  const handleEmailChange = useCallback((event) => {
    setEmail(event.target.value);
  }, []);

  const handlePasswordChange = useCallback((event) => {
    setPassword(event.target.value);
  }, []);

  return (
    <>
      {message ? (
        <p className="mb-3 text-sm text-slate-300">{message}</p>
      ) : null}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="login-email" className="block text-sm text-slate-400 mb-1">
            Email
          </label>
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={handleEmailChange}
            required
            className="w-full px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-600 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <PasswordField
          id="login-password"
          label="Password"
          value={password}
          onChange={handlePasswordChange}
        />

        {error ? (
          <p className="text-sm text-red-400">{error}</p>
        ) : null}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold transition"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-slate-400">
        No account?{" "}
        <button
          type="button"
          onClick={handleSwitchToSignup}
          className="text-emerald-400 hover:text-emerald-300 font-medium"
        >
          Sign up
        </button>
      </p>
    </>
  );
};

export default LoginForm;

