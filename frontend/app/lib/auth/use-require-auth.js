import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/app/lib/auth/use-auth";

export const useRequireAuth = (redirectPath) => {
  const router = useRouter();
  const { jwt, loading: authLoading, restoringAuth, isAuthenticated } = useAuth();

  useEffect(() => {
    if (authLoading || restoringAuth) return;
    if (!jwt || !isAuthenticated) {
      sessionStorage.setItem("redirectAfterAuth", redirectPath);
      router.replace("/?auth=signup");
    }
  }, [redirectPath, jwt, authLoading, restoringAuth, isAuthenticated, router]);

  const isReady = !authLoading && !restoringAuth && !!jwt && isAuthenticated;
  return { isReady };
};
