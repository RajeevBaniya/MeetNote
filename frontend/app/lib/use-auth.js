import { useContext } from "react";
import { AuthContext } from "@/app/providers/auth-provider";

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  const isAuthenticated = Boolean(ctx.jwt && ctx.user);
  return {
    ...ctx,
    isAuthenticated,
  };
}
