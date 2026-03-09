"use client";

import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/app/lib/auth/use-require-auth";
import Navbar from "@/app/components/landing/navbar";

const pageBackground = (
  <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.25),transparent_55%)]" />
);

const FeaturesPage = () => {
  const router = useRouter();
  const { isReady } = useRequireAuth("/features");

  const openSummarizer = () => {
    router.push("/summarize?source=upload");
  };

  const openHistory = () => {
    router.push("/features/history");
  };

  if (!isReady) {
    return (
      <div className="relative min-h-screen bg-[#0f1419] text-slate-100">
        {pageBackground}
        <Navbar />
        <div className="relative flex flex-1 items-center justify-center py-20">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
            <p className="mt-4 text-sm text-slate-400">Redirecting…</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-[#0f1419] text-slate-100">
      {pageBackground}
      <Navbar />

      <main className="relative mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
              Features
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Tools to capture and organize what matters from your meetings.
            </p>
          </div>
          <button
            type="button"
            onClick={openHistory}
            className="shrink-0 self-start rounded-lg border border-slate-600 bg-slate-800/60 px-4 py-2.5 text-sm font-semibold text-slate-100 transition hover:border-slate-500 hover:bg-slate-700/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f1419]"
          >
            History
          </button>
        </div>

        <section className="space-y-6 sm:space-y-8">
          <div
            className="group flex flex-col gap-4 rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-5 transition hover:border-slate-600 sm:flex-row sm:items-center sm:justify-between sm:px-5 sm:py-5"
            role="article"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    className="h-5 w-5"
                    aria-hidden
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5v-7.5H8.25v7.5z"
                    />
                  </svg>
                </span>
                <div>
                  <h2 className="text-base font-medium text-slate-100 sm:text-lg">
                    Summarize Meetings
                  </h2>
                  <p className="mt-0.5 text-sm text-slate-400">
                    Upload a transcript or paste text and get a summary with
                    action items and decisions.
                  </p>
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={openSummarizer}
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f1419]"
            >
              Open Summarizer
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="h-4 w-4"
                aria-hidden
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
                />
              </svg>
            </button>
          </div>
        </section>
      </main>
    </div>
  );
};

export default FeaturesPage;
