"use client";

import { useCallback } from "react";

const SORT_OPTIONS = [
  { value: "created_at", label: "Created Date" },
  { value: "meeting_date", label: "Meeting Date" },
  { value: "meeting_title", label: "Title" },
  { value: "updated_at", label: "Last Updated" },
];

const SortDropdown = ({ sortBy, sortOrder, onSortChange }) => {
  const handleSortByChange = useCallback(
    (e) => {
      onSortChange({ sortBy: e.target.value, sortOrder });
    },
    [sortOrder, onSortChange]
  );

  const handleSortOrderToggle = useCallback(() => {
    const newOrder = sortOrder === "desc" ? "asc" : "desc";
    onSortChange({ sortBy, sortOrder: newOrder });
  }, [sortBy, sortOrder, onSortChange]);

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1.5 text-xs text-slate-500">
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
        </svg>
        <span className="font-medium">Sort</span>
      </div>
      <select
        value={sortBy}
        onChange={handleSortByChange}
        className="px-3 py-2 bg-slate-800/60 border border-slate-700/60 rounded-xl text-slate-100 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/40 transition-all hover:border-slate-600 cursor-pointer"
      >
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value} className="bg-slate-800">
            {option.label}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={handleSortOrderToggle}
        className={`p-2 rounded-xl border transition-all duration-200 ${
          sortOrder === "asc"
            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
            : "bg-slate-800/60 border-slate-700/60 text-slate-400 hover:text-slate-200 hover:border-slate-600"
        }`}
        title={sortOrder === "desc" ? "Newest first" : "Oldest first"}
      >
        <svg
          className={`h-4 w-4 transition-transform duration-300 ${sortOrder === "asc" ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
    </div>
  );
};

export default SortDropdown;
