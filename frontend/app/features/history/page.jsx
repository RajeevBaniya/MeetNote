"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/app/lib/auth/use-require-auth";
import Navbar from "@/app/components/landing/navbar";
import HistoryView from "@/app/summarize/components/HistoryView";

const pageBackground = (
  <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.25),transparent_55%)]" />
);

const FeaturesHistoryPage = () => {
  const router = useRouter();
  const { isReady } = useRequireAuth("/features/history");

  const handleSelectSummary = (summary) => {
    router.push(`/summarize?id=${summary.id}`);
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
        <div className="mb-8">
          <Link
            href="/features"
            className="inline-flex items-center gap-1.5 text-sm text-slate-400 transition hover:text-slate-200"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="h-4 w-4"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Features
          </Link>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            History
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Summaries created from file uploads only.
          </p>
        </div>

        <HistoryView
          onSelectSummary={handleSelectSummary}
          uploadOnly={true}
        />
      </main>
    </div>
  );
};

export default FeaturesHistoryPage;
