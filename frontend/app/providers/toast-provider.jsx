"use client";

import { useToastHost } from "@/app/lib/ui/use-toast";

const ToastProvider = ({ children }) => {
  const { items, dismiss } = useToastHost();

  return (
    <>
      {children}
      <div className="fixed top-4 right-4 z-9999 flex flex-col gap-2 pointer-events-none">
        {items.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => dismiss(t.id)}
            className="pointer-events-auto max-w-[320px] rounded-lg border border-slate-700/60 bg-slate-900/95 px-4 py-3 text-sm text-slate-100 shadow-xl backdrop-blur-sm text-left"
          >
            {t.message}
          </button>
        ))}
      </div>
    </>
  );
};

export default ToastProvider;

