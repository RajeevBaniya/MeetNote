"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/app/lib/auth/use-auth";
import LoginForm from "@/app/components/auth/login-form";
import SignupForm from "@/app/components/auth/signup-form";

const AuthModal = ({ mode, onClose, message }) => {
  const router = useRouter();
  const { setError } = useAuth();
  const [currentMode, setCurrentMode] = useState(mode);

  const isSignup = currentMode === "signup";

  const handleSuccess = useCallback(() => {
    onClose();
    const redirectPath = sessionStorage.getItem("redirectAfterAuth");
    if (redirectPath) {
      sessionStorage.removeItem("redirectAfterAuth");
      router.push(redirectPath);
    } else {
      router.push("/");
    }
  }, [onClose, router]);

  const handleSwitchMode = useCallback(
    (nextMode) => {
      setCurrentMode(nextMode);
      setError(null);
    },
    [setError],
  );

  const handleBackdropClick = useCallback(() => {
    onClose();
  }, [onClose]);

  const handleContentClick = useCallback((event) => {
    event.stopPropagation();
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={handleBackdropClick}
    >
      <div
        className="w-full max-w-sm rounded-xl border border-slate-600/50 bg-slate-800/95 p-6 shadow-2xl"
        onClick={handleContentClick}
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

        {currentMode === "signup" ? (
          <SignupForm
            onSuccess={handleSuccess}
            onSwitchMode={handleSwitchMode}
            message={message}
          />
        ) : (
          <LoginForm
            onSuccess={handleSuccess}
            onSwitchMode={handleSwitchMode}
            message={message}
          />
        )}
      </div>
    </div>
  );
};

export default AuthModal;

