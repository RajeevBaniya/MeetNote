"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FiVideo } from "react-icons/fi";

const NAV_LINKS = [
  { id: "about", label: "About" },
  { id: "pricing", label: "Pricing" },
  { id: "contact", label: "Contact" },
];

const Navbar = () => {
  const [hasScrolled, setHasScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const isScrolled = window.scrollY > 10;
      setHasScrolled((previous) =>
        previous === isScrolled ? previous : isScrolled,
      );
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll);

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  const logoTextClassName = hasScrolled
    ? "text-base font-semibold tracking-tight text-emerald-400"
    : "text-base font-semibold tracking-tight text-white";

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-black/20 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
        >
          <FiVideo className="h-5 w-5 text-emerald-400" />
          <span className={logoTextClassName}>MeetNote</span>
        </Link>

        <div className="flex items-center gap-3">
          <nav className="hidden items-center gap-6 text-sm text-white/80 sm:flex">
            {NAV_LINKS.map((item) => (
              <button
                key={item.id}
                type="button"
                disabled
                className="rounded-md px-2 py-1 text-white/70 cursor-default"
              >
                {item.label}
              </button>
            ))}
            <details className="relative">
              <summary className="flex cursor-pointer list-none items-center gap-1 rounded-md px-2 py-1 font-medium text-white/85 transition hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60">
                <span>Meet</span>
                <span aria-hidden="true">▾</span>
              </summary>
              <div className="absolute right-0 mt-2 w-44 rounded-xl border border-white/10 bg-neutral-950 p-2 shadow-xl ring-1 ring-white/10">
                <Link
                  href="/meeting/join?mode=host"
                  className="block rounded-lg px-3 py-2 text-sm text-white/80 transition hover:bg-white/10 hover:text-white"
                >
                  Host a meeting
                </Link>
                <Link
                  href="/meeting/join?mode=join"
                  className="mt-1 block rounded-lg px-3 py-2 text-sm text-white/80 transition hover:bg-white/10 hover:text-white"
                >
                  Join a meeting
                </Link>
              </div>
            </details>
          </nav>

          <details className="relative sm:hidden">
            <summary className="list-none rounded-lg bg-white/10 px-3 py-2 text-sm font-semibold text:white ring-1 ring-white/15 transition hover:bg-white/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60">
              Menu
            </summary>
            <div className="absolute right-0 mt-2 w-48 rounded-xl border border-white/10 bg-neutral-950 p-2 shadow-xl ring-1 ring-white/10">
              {NAV_LINKS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  disabled
                  className="block w-full rounded-lg px-3 py-2 text-left text-sm text-white/70 cursor-default"
                >
                  {item.label}
                </button>
              ))}
              <div className="mt-1 rounded-lg bg-white/5 p-1">
                <p className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white/40">
                  Meet
                </p>
                <Link
                  href="/meeting/join?mode=host"
                  className="block rounded-lg px-3 py-2 text-sm text-white/80 transition hover:bg-white/10 hover:text-white"
                >
                  Host a meeting
                </Link>
                <Link
                  href="/meeting/join?mode=join"
                  className="mt-1 block rounded-lg px-3 py-2 text-sm text-white/80 transition hover:bg-white/10 hover:text-white"
                >
                  Join a meeting
                </Link>
              </div>
            </div>
          </details>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
