/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter, useParams } from "next/navigation";
import StreamProvider from "@/app/components/stream-provider";
import MeetingRoom from "@/app/components/meeting-room/meeting-room";
import { StreamTheme } from "@stream-io/video-react-sdk";
import { useAuth } from "@/app/hooks/use-auth";
import { useStreamTokenFromBackend } from "@/app/hooks/use-stream-token";

const MeetingPage = () => {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user: authUser, jwt, loading: authLoading, restoringAuth, isAuthenticated } = useAuth();

  const callId = params.id;
  const queryName = searchParams.get("name");
  const displayName =
    (queryName && queryName.trim()) ||
    (authUser && (authUser.name || authUser.email || authUser.id)) ||
    "anonymous";

  useEffect(() => {
    if (authLoading || restoringAuth) return;
    
    if (!jwt || !isAuthenticated) {
      const currentPath = `/meeting/${callId}`;
      const queryString = searchParams.toString();
      const fullPath = queryString ? `${currentPath}?${queryString}` : currentPath;
      sessionStorage.setItem("redirectAfterAuth", fullPath);
      
      const timer = setTimeout(() => {
        router.replace("/?auth=login&reason=meeting");
      }, 800);
      
      return () => clearTimeout(timer);
    }
  }, [jwt, authLoading, restoringAuth, isAuthenticated, callId, searchParams, router]);

  const { token, user, error, status } = useStreamTokenFromBackend(
    callId,
    jwt,
    displayName
  );

  const handleLeave = () => {
    router.push("/");
  };

  if (authLoading || restoringAuth) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-emerald-500 mx-auto" />
          <p className="mt-4 text-lg text-slate-300">
            {restoringAuth ? "Restoring session…" : "Loading…"}
          </p>
        </div>
      </div>
    );
  }

  if (!jwt || !isAuthenticated) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-emerald-500 mx-auto" />
          <p className="mt-4 text-lg text-slate-300">Redirecting…</p>
        </div>
      </div>
    );
  }

  if (error && status === "error") {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
        <div className="p-6 bg-red-900/20 border border-red-500 rounded-lg">
          <p className="text-red-500 font-bold text-lg mb-2">Error</p>
          <p>{error}</p>
          <button
            onClick={() => router.push("/")}
            className="mt-4 px-4 py-2 bg-red-500 rounded-lg hover:bg-red-600"
          >
            Back
          </button>
        </div>
      </div>
    );
  }

  if (status === "waiting_approval") {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-amber-500 mx-auto" />
          <p className="mt-4 text-lg text-slate-300">
            Waiting for host approval
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Retrying in a few seconds…
          </p>
        </div>
      </div>
    );
  }

  if (status !== "ready" || !token || !user) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-emerald-500 mx-auto" />
          <p className="mt-4 text-lg text-slate-300">Connecting to meeting…</p>
        </div>
      </div>
    );
  }

  return (
    <StreamProvider user={user} token={token}>
      <StreamTheme>
        <MeetingRoom
          callId={callId}
          onLeave={handleLeave}
          userId={user.id}
          jwt={jwt}
        />
      </StreamTheme>
    </StreamProvider>
  );
};

export default MeetingPage;
