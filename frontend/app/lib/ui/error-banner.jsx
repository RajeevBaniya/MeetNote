"use client";

import { memo } from "react";

const ErrorBanner = ({ message, onClose }) => {
  if (!message) return null;

  return (
    <div className="mb-3 flex items-start justify-between rounded-lg border border-red-500/40 bg-red-950/60 px-3 py-2 text-sm text-red-100 shadow-sm">
      <div className="flex items-start gap-2">
        <span aria-hidden="true" className="mt-0.5 text-red-300">
          ⚠
        </span>
        <p className="leading-snug">{message}</p>
      </div>
      {typeof onClose === "function" ? (
        <button
          type="button"
          aria-label="Dismiss message"
          onClick={onClose}
          className="ml-2 rounded-full px-1 text-xs text-red-200 hover:bg-red-900/70 hover:text-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
        >
          ×
        </button>
      ) : null}
    </div>
  );
};

export default memo(ErrorBanner);

