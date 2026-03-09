import { useContext } from "react";

import { AuthContext } from "@/app/lib/auth/auth-context";

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  const isAuthenticated = Boolean(ctx.jwt && ctx.user);
  return {
    ...ctx,
    isAuthenticated,
  };
};
