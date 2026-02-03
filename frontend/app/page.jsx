"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Navbar from "@/app/components/landing/navbar";
import HeroSection from "@/app/components/landing/hero";
import AuthModal from "@/app/components/auth/auth-modal";

const HomePage = () => {
  const searchParams = useSearchParams();
  const [authModal, setAuthModal] = useState(null);

  useEffect(() => {
    const authParam = searchParams.get("auth");
    const reasonParam = searchParams.get("reason");

    if (authParam === "login" || authParam === "signup") {
      const message =
        reasonParam === "meeting"
          ? "Please sign in or sign up to create or join a meeting."
          : null;
      setAuthModal({ mode: authParam, message });
    }
  }, [searchParams]);

  const openAuth = (mode) => {
    setAuthModal({ mode, message: null });
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#0f1419] text-slate-100">
      <Navbar onOpenAuth={openAuth} />
      <main className="flex flex-1">
        <HeroSection onOpenAuth={openAuth} />
      </main>
      {authModal ? (
        <AuthModal
          mode={authModal.mode}
          message={authModal.message}
          onClose={() => setAuthModal(null)}
        />
      ) : null}
    </div>
  );
};

export default HomePage;
