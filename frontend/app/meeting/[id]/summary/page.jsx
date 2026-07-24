"use client";

import { useEffect, useState, Suspense } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/app/lib/auth/use-auth";
import Navbar from "@/app/components/landing/navbar";
import { Info, MessageSquare, FileText, BarChart2, Video } from "lucide-react";

import MeetingOverview from "./components/meeting-overview";
import MeetingChat from "./components/meeting-chat";
import MeetingSummaries from "./components/meeting-summaries";
import MeetingInsights from "./components/meeting-insights";
import MeetingRecording from "./components/meeting-recording";

const pageBackground = (
  <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.2),transparent_55%)]" />
);

const ENDED_BANNER_MESSAGE = "This meeting has ended. You were redirected here from the call.";

const SummaryPageContent = () => {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { jwt, loading: authLoading, restoringAuth, isAuthenticated } = useAuth();

  const showEndedBanner = searchParams.get("ended") === "1";
  const [meeting, setMeeting] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const usesInternalScroll = activeTab === "chat";

  // Chat status is fetched once here and passed to the components that need it.
  // This eliminates duplicate network requests from child components.
  const [chatStatus, setChatStatus] = useState(null);
  const [chatStatusLoading, setChatStatusLoading] = useState(false);

  const meetingId = params.id;

  useEffect(() => {
    if (authLoading || restoringAuth) return;
    if (!jwt || !isAuthenticated) {
      const path = `/meeting/${meetingId}/summary`;
      sessionStorage.setItem("redirectAfterAuth", path);
      router.replace("/?auth=login&reason=meeting");
      return;
    }
  }, [jwt, authLoading, restoringAuth, isAuthenticated, meetingId, router]);

  // Fetch meeting metadata and chat status in parallel on mount
  useEffect(() => {
    if (!meetingId || !jwt) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setNotFound(false);
    setChatStatusLoading(true);
    setChatStatus(null);

    const meetingFetch = fetch(`${apiUrl}/meetings/${meetingId}`, {
      headers: { Authorization: `Bearer ${jwt}` },
    }).then((r) => {
      if (r.status === 404) return null;
      if (!r.ok) throw new Error(r.statusText);
      return r.json();
    });

    const statusFetch = fetch(`${apiUrl}/meetings/${meetingId}/chat-status`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null);

    Promise.all([meetingFetch, statusFetch])
      .then(([meetingData, statusData]) => {
        if (cancelled) return;
        if (meetingData === null) {
          setNotFound(true);
          setMeeting(null);
        } else {
          setMeeting(meetingData);
          setNotFound(false);
        }
        setChatStatus(statusData);
      })
      .catch((err) => {
        if (!cancelled) {
          setNotFound(true);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
          setChatStatusLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [meetingId, jwt]);

  useEffect(() => {
    if (meeting?.is_active && meetingId) {
      router.replace(`/meeting/${meetingId}`);
    }
  }, [meeting?.is_active, meetingId, router]);

  const handleBack = () => {
    router.push("/");
  };

  const openAuth = (mode) => {
    router.push(`/?auth=${mode}`);
  };

  const tabs = [
    { id: "overview", label: "Overview", icon: Info },
    { id: "chat", label: "AI Chat", icon: MessageSquare },
    { id: "summaries", label: "Summaries", icon: FileText },
    { id: "insights", label: "Insights", icon: BarChart2 },
    { id: "recording", label: "Recording", icon: Video },
  ];

  const LayoutWithNav = ({ children }) => {
    return (
      <div className="relative min-h-screen bg-[#0f1419] text-slate-100 flex flex-col">
        {pageBackground}
        <Navbar onOpenAuth={openAuth} />
        {children}
      </div>
    );
  };

  if (authLoading || restoringAuth) {
    return (
      <LayoutWithNav>
        <div className="relative flex flex-1 items-center justify-center py-20">
          <div className="text-center">
            <div className="mx-auto h-14 w-14 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
            <p className="mt-4 text-slate-400">Loading…</p>
          </div>
        </div>
      </LayoutWithNav>
    );
  }

  if (!jwt || !isAuthenticated) {
    return (
      <LayoutWithNav>
        <div className="relative flex flex-1 items-center justify-center py-20">
          <div className="text-center">
            <div className="mx-auto h-14 w-14 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
            <p className="mt-4 text-slate-400">Redirecting…</p>
          </div>
        </div>
      </LayoutWithNav>
    );
  }

  if (loading) {
    return (
      <LayoutWithNav>
        <div className="relative flex flex-1 items-center justify-center py-20">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
            <p className="mt-4 text-sm text-slate-500">Loading meeting…</p>
          </div>
        </div>
      </LayoutWithNav>
    );
  }

  if (notFound || !meeting) {
    return (
      <LayoutWithNav>
        <main className="relative mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8 flex-1">
          <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 px-5 py-8 text-center">
            <p className="mb-4 text-sm text-slate-400">Meeting not found.</p>
            <button
              type="button"
              onClick={handleBack}
              className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 focus:outline-none"
            >
              Back to home
            </button>
          </div>
        </main>
      </LayoutWithNav>
    );
  }

  return (
    <LayoutWithNav>
      {showEndedBanner ? (
        <div className="relative mx-auto w-full max-w-4xl px-4 pt-6 sm:px-6 lg:px-8 shrink-0">
          <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            {ENDED_BANNER_MESSAGE}
          </div>
        </div>
      ) : null}

      <main className={`relative mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8 flex-1 flex flex-col ${usesInternalScroll ? "min-h-0" : ""}`}>
        {/* Title */}
        <div className="mb-6 shrink-0">
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            {meeting.title || "Untitled Meeting"}
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Meeting ID: {meetingId}
          </p>
        </div>

        {/* Tab Headers */}
        <div className="flex border-b border-slate-800 mb-6 shrink-0 overflow-x-auto custom-scrollbar gap-1.5 sm:gap-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-4 py-3 border-b-2 text-sm font-medium transition whitespace-nowrap focus:outline-none ${
                  isActive
                    ? "border-emerald-500 text-emerald-400 font-semibold"
                    : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Content Panels */}
        <div className={`flex-1 ${usesInternalScroll ? "min-h-0" : ""}`}>
          {activeTab === "overview" && (
            <MeetingOverview
              meetingId={meetingId}
              jwt={jwt}
              meeting={meeting}
              chatStatus={chatStatus}
              chatStatusLoading={chatStatusLoading}
            />
          )}
          {activeTab === "chat" && (
            <MeetingChat
              meetingId={meetingId}
              jwt={jwt}
              chatStatus={chatStatus}
              chatStatusLoading={chatStatusLoading}
            />
          )}
          {activeTab === "summaries" && (
            <MeetingSummaries meetingId={meetingId} meetingTitle={meeting.title} />
          )}
          {activeTab === "insights" && (
            <MeetingInsights meetingId={meetingId} jwt={jwt} meeting={meeting} />
          )}
          {activeTab === "recording" && (
            <MeetingRecording meetingId={meetingId} jwt={jwt} />
          )}
        </div>
      </main>
    </LayoutWithNav>
  );
};

const SummaryPage = () => {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#0f1419] text-slate-100 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-2 border-slate-600 border-t-emerald-500" />
        </div>
      }
    >
      <SummaryPageContent />
    </Suspense>
  );
};

export default SummaryPage;
