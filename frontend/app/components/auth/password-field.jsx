"use client";

import { useState } from "react";

const inputClass =
  "w-full px-3 py-2.5 pr-10 rounded-lg bg-slate-900 border border-slate-600 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500";
const toggleBtnClass =
  "absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded text-slate-400 hover:text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-inset";

function EyeIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="w-5 h-5"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639-.04.132-.144.318-.32.61C19.448 15.396 16.04 18.75 12 18.75c-4.04 0-7.448-3.354-9.679-7.323z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  );
}

function EyeSlashIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="w-5 h-5"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-1.765 2.257"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6.228 18.75a10.45 10.45 0 005.772 1.75c4.756 0 8.773-3.162 10.065-7.498a10.523 10.523 0 00-1.765-2.257M17.535 17.535C19.076 15.352 20 12.786 20 12c0-2.786-.924-5.352-2.465-7.282M6.228 6.228a10.45 10.45 0 011.757-1.204"
      />
    </svg>
  );
}

function PasswordField({ id, label, value, onChange, required = true }) {
  const [showPassword, setShowPassword] = useState(false);
  const toggleLabel = showPassword ? "Hide password" : "Show password";

  return (
    <div>
      <label htmlFor={id} className="block text-sm text-slate-400 mb-1">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={showPassword ? "text" : "password"}
          value={value}
          onChange={onChange}
          required={required}
          className={inputClass}
        />
        <button
          type="button"
          onClick={() => setShowPassword((prev) => !prev)}
          className={toggleBtnClass}
          title={toggleLabel}
          aria-label={toggleLabel}
        >
          {showPassword ? <EyeSlashIcon /> : <EyeIcon />}
        </button>
      </div>
    </div>
  );
}

export default PasswordField;
