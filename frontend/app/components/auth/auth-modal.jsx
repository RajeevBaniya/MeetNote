"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/app/hooks/use-auth";

const AuthModal = ({ mode, onClose, message }) => {
  const router = useRouter();
  const { login, register, loading, error, setError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [currentMode, setCurrentMode] = useState(mode);

  const isSignup = currentMode === "signup";

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    const ok = isSignup
      ? await register(email.trim(), password)
      : await login(email.trim(), password);

    if (ok) {
      onClose();
      const redirectPath = sessionStorage.getItem("redirectAfterAuth");
      if (redirectPath) {
        sessionStorage.removeItem("redirectAfterAuth");
        router.push(redirectPath);
      } else {
        router.push("/");
      }
    }
  };

  const switchMode = () => {
    setCurrentMode(isSignup ? "login" : "signup");
    setError(null);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-xl border border-slate-600/50 bg-slate-800/95 p-6 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-xl font-semibold text-slate-100">
            {isSignup ? "Sign up" : "Sign in"}
          </h1>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {message ? (
          <p className="mb-3 text-sm text-slate-300">{message}</p>
        ) : null}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm text-slate-400 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              className="w-full px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-600 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm text-slate-400 mb-1"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              className="w-full px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-600 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          {error ? (
            <p className="text-sm text-red-400">{error}</p>
          ) : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold transition"
          >
            {loading
              ? isSignup
                ? "Creating account…"
                : "Signing in…"
              : isSignup
                ? "Sign up"
                : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-400">
          {isSignup ? "Already have an account?" : "No account?"}{" "}
          <button
            type="button"
            onClick={switchMode}
            className="text-emerald-400 hover:text-emerald-300 font-medium"
          >
            {isSignup ? "Sign in" : "Sign up"}
          </button>
        </p>
      </div>
    </div>
  );
};

export default AuthModal;
