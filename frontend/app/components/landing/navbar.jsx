"use client";

import Link from "next/link";
import { useEffect, useState, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import { FiVideo } from "react-icons/fi";
import { useAuth } from "@/app/hooks/use-auth";

const Navbar = ({ onOpenAuth }) => {
  const [hasScrolled, setHasScrolled] = useState(false);
  const [meetOpen, setMeetOpen] = useState(false);
  const meetRef = useRef(null);
  const { isAuthenticated, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

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

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (meetRef.current && !meetRef.current.contains(event.target)) {
        setMeetOpen(false);
      }
    };
    if (meetOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [meetOpen]);

  const logoTextClassName = hasScrolled
    ? "text-base font-semibold tracking-tight text-emerald-400"
    : "text-base font-semibold tracking-tight text-white";

  const handleAuthClick = (mode) => {
    if (pathname === "/" && onOpenAuth) {
      onOpenAuth(mode);
    } else {
      router.push(`/?auth=${mode}`);
    }
  };

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
            <div className="relative" ref={meetRef}>
              <button
                type="button"
                onClick={() => setMeetOpen((prev) => !prev)}
                className="flex cursor-pointer list-none items-center gap-1 rounded-md px-2 py-1 font-medium text-white/85 transition hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
                aria-expanded={meetOpen}
                aria-haspopup="true"
              >
                <span>Meet</span>
                <span aria-hidden="true">▾</span>
              </button>
              {meetOpen ? (
                <div className="absolute right-0 mt-2 w-44 rounded-xl border border-white/10 bg-neutral-950 p-2 shadow-xl ring-1 ring-white/10">
                  <Link
                    href="/meeting/join?mode=host"
                    className="block rounded-lg px-3 py-2 text-sm text-white/80 transition hover:bg-white/10 hover:text-white"
                    onClick={() => setMeetOpen(false)}
                  >
                    Host a meeting
                  </Link>
                  <Link
                    href="/meeting/join?mode=join"
                    className="mt-1 block rounded-lg px-3 py-2 text-sm text-white/80 transition hover:bg-white/10 hover:text-white"
                    onClick={() => setMeetOpen(false)}
                  >
                    Join a meeting
                  </Link>
                </div>
              ) : null}
            </div>
            {isAuthenticated ? (
              <Link
                href="/meetings"
                className="rounded-md px-2 py-1 font-medium text-white/85 transition hover:text-white"
              >
                My meetings
              </Link>
            ) : null}
            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => logout()}
                className="rounded-md px-2 py-1 font-medium text-red-400 transition hover:text-red-300"
              >
                Log out
              </button>
            ) : (
              <button
                type="button"
                onClick={() => handleAuthClick("signup")}
                className="rounded-md px-2 py-1 font-medium text-emerald-400 transition hover:text-emerald-300"
              >
                Sign up
              </button>
            )}
          </nav>

          <details className="relative sm:hidden">
            <summary className="list-none rounded-lg bg-white/10 px-3 py-2 text-sm font-semibold text:white ring-1 ring-white/15 transition hover:bg-white/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60">
              Menu
            </summary>
            <div className="absolute right-0 mt-2 w-48 rounded-xl border border-white/10 bg-neutral-950 p-2 shadow-xl ring-1 ring-white/10">
              {isAuthenticated ? (
                <button
                  type="button"
                  onClick={() => logout()}
                  className="block w-full text-left rounded-lg px-3 py-2 text-sm text-red-400 transition hover:bg-red-400/20"
                >
                  Log out
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => handleAuthClick("signup")}
                  className="block w-full text-left rounded-lg px-3 py-2 text-sm text-emerald-400 transition hover:bg-emerald-300/20"
                >
                  Sign up
                </button>
              )}
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
                {isAuthenticated ? (
                  <Link
                    href="/meetings"
                    className="mt-1 block rounded-lg px-3 py-2 text-sm text-white/80 transition hover:bg-white/10 hover:text-white"
                  >
                    My meetings
                  </Link>
                ) : null}
              </div>
            </div>
          </details>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
