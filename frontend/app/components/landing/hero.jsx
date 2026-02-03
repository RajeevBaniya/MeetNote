"use client";

import Image from "next/image";
import Link from "next/link";
import { useAuth } from "@/app/hooks/use-auth";
import { useRouter } from "next/navigation";

const HeroSection = ({ onOpenAuth }) => {
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

  return (
    <section className="relative flex w-full items-center overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.25),transparent_55%)]" />
      <div className="mx-auto flex w-full max-w-6xl items-center px-4 py-8 sm:px-6 sm:py-12 lg:max-w-7xl lg:py-16 xl:px-10">
        <div className="flex w-full flex-col gap-10 lg:flex-row lg:items-center">
          <div className="max-w-3xl text-center xl:max-w-4xl lg:text-left">
            <p className="text-sm font-bold text-emerald-400" id="product">
              MeetNote
            </p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-50 sm:text-5xl lg:text-6xl xl:text-7xl">
              Video meetings with live transcripts and clear summaries.
            </h1>
            <p className="mt-5 mx-auto max-w-2xl text-base leading-relaxed text-slate-300 sm:text-lg lg:mx-0">
              <span className="font-semibold text-emerald-400">MeetNote</span>{" "}
              helps your team stay focused during the call and aligned after it
              ends. Capture decisions, action items and context without extra
              notes.
            </p>

            <div className="mt-8 flex flex-row flex-wrap items-center justify-center gap-3 lg:justify-start">
              <button
                type="button"
                onClick={handleGetStarted}
                className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-5 py-3 text-sm font-semibold text-white ring-1 ring-emerald-500 transition hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
              >
                {isAuthenticated ? "Start Meeting" : "Get Started"}
              </button>
              <Link
                href="#product"
                className="inline-flex items-center justify-center rounded-lg bg-slate-800 px-5 py-3 text-sm font-semibold text-slate-100 ring-1 ring-slate-700 transition hover:bg-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/60"
              >
                Explore features
              </Link>
            </div>
          </div>

          <div className="w-full max-w-md lg:max-w-lg xl:max-w-xl mx-auto lg:mx-0">
            <div className="w-full rounded-2xl border border-emerald-500/70 ring-1 ring-emerald-400/60 shadow-[0_0_35px_rgba(16,185,129,0.35)] animate-pulse">
              <Image
                src="/images/hero.png"
                alt="Preview of a MeetNote meeting with participants, transcripts, and notes"
                width={1087}
                height={645}
                className="h-auto w-full rounded-2xl object-contain"
                sizes="(min-width: 1280px) 520px, (min-width: 1024px) 460px, (min-width: 768px) 420px, 90vw"
                priority
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
