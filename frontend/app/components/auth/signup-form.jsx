"use client";

import { useState } from "react";
import { useAuth } from "@/app/lib/use-auth";
import PasswordField from "@/app/components/auth/password-field";

const SignupForm = ({ onSuccess, onSwitchMode, message }) => {
  const { register, loading, error, setError } = useAuth();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    const ok = await register(email.trim(), password, name.trim() || null);
    if (ok && typeof onSuccess === "function") {
      onSuccess();
    }
  };

  return (
    <>
      {message ? (
        <p className="mb-3 text-sm text-slate-300">{message}</p>
      ) : null}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="signup-email"
            className="block text-sm text-slate-400 mb-1"
          >
            Email
          </label>
          <input
            id="signup-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            className="w-full px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-600 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label
            htmlFor="signup-name"
            className="block text-sm text-slate-400 mb-1"
          >
            Display name <span className="text-slate-500">(optional)</span>
          </label>
          <input
            id="signup-name"
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={255}
            className="w-full px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-600 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 placeholder:text-slate-500"
          />
        </div>

        <PasswordField
          id="signup-password"
          label="Password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {error ? <p className="text-sm text-red-400">{error}</p> : null}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold transition"
        >
          {loading ? "Creating account…" : "Sign up"}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-slate-400">
        Already have an account?{" "}
        <button
          type="button"
          onClick={() => {
            if (typeof onSwitchMode === "function") onSwitchMode("login");
            setError(null);
          }}
          className="text-emerald-400 hover:text-emerald-300 font-medium"
        >
          Sign in
        </button>
      </p>
    </>
  );
};

export default SignupForm;
