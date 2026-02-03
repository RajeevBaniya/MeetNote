"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

export default function MeetingLayout({ children }) {
  const pathname = usePathname();

  useEffect(() => {
    const isCallPage = pathname?.startsWith("/meeting/") && !pathname?.endsWith("/join");
    const html = document.documentElement;
    if (isCallPage) {
      html.classList.add("meeting-page");
    } else {
      html.classList.remove("meeting-page");
    }
    return () => html.classList.remove("meeting-page");
  }, [pathname]);

  return (
    <div className="fixed inset-0 w-full h-full overflow-hidden bg-[#020617]">
      {children}
    </div>
  );
}
