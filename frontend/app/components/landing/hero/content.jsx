"use client";

import { useAuth } from "@/app/lib/use-auth";
import { useRouter } from "next/navigation";

function Content({ onOpenAuth }) {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  const handleGetStarted = () => {
    if (isAuthenticated) {
      router.push("/meeting/join?mode=host");
    } else if (onOpenAuth) {
      onOpenAuth("signup");
    } else {
      router.push("/?auth=signup");
    }
  };

  const handleExploreFeatures = () => {
    if (isAuthenticated) {
      router.push("/features");
    } else if (onOpenAuth) {
      onOpenAuth("signup");
    } else {
      router.push("/?auth=signup");
    }
  };

  return (
    <div className="max-w-3xl text-center xl:max-w-4xl lg:text-left">
      <p className="text-sm font-bold text-emerald-400" id="product">
        MeetNote
      </p>
      <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-50 sm:text-5xl lg:text-6xl xl:text-7xl">
        Video meetings with live transcripts and clear summaries
      </h1>
      <p className="mt-5 mx-auto max-w-2xl text-base leading-relaxed text-slate-300 sm:text-lg lg:mx-0">
        <span className="font-semibold text-emerald-400">MeetNote</span>{" "}
        helps your team stay focused during the call and aligned after it
        ends. Capture decisions, action items and context without extra
        notes.
      </p>
      <div className="mt-6 sm:mt-8 flex flex-row flex-wrap items-center justify-center gap-2.5 sm:gap-3 lg:justify-start">
        <button
          type="button"
          onClick={handleGetStarted}
          className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-5 py-3 text-sm font-semibold text-white ring-1 ring-emerald-500 transition hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
        >
          {isAuthenticated ? "Start Meeting" : "Get Started"}
        </button>
        <button
          type="button"
          onClick={handleExploreFeatures}
          className="inline-flex items-center justify-center rounded-lg bg-slate-800 px-5 py-3 text-sm font-semibold text-slate-100 ring-1 ring-slate-700 transition hover:bg-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/60"
        >
          Explore features
        </button>
      </div>
    </div>
  );
}

export default Content;
