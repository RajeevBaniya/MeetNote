"use client";

import { useCallback, useRef } from "react";

const MEETING_TYPES = [
  { value: "", label: "All Types" },
  { value: "team", label: "Team Meeting" },
  { value: "one-on-one", label: "1-on-1" },
  { value: "client", label: "Client Meeting" },
  { value: "standup", label: "Standup" },
  { value: "project-review", label: "Project Review" },
  { value: "brainstorm", label: "Brainstorming" },
  { value: "interview", label: "Interview" },
  { value: "training", label: "Training" },
  { value: "other", label: "Other" },
];

function FilterPanel({ filters, onFilterChange, isExpanded, onToggle }) {
  const handleClearFilters = useCallback(() => {
    onFilterChange({
      dateFrom: null,
      dateTo: null,
      meetingType: null,
      tags: [],
    });
  }, [onFilterChange]);

  const hasActiveFilters =
    filters.dateFrom ||
    filters.dateTo ||
    filters.meetingType ||
    (filters.tags && filters.tags.length > 0);

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button
        type="button"
        onClick={onToggle}
        className={`group flex items-center gap-2 px-3 sm:px-3 py-2 text-sm font-medium rounded-lg border transition-all duration-200 touch-manipulation min-h-[44px] ${
          isExpanded
            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
            : "bg-slate-800/60 border-slate-700/60 text-slate-300 hover:text-slate-100 hover:border-slate-600 hover:bg-slate-800 active:bg-slate-800"
        }`}
      >
        <svg
          className="h-4 w-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
          />
        </svg>
        <span>Filters</span>
        {hasActiveFilters && (
          <span className="flex items-center justify-center w-5 h-5 text-xs font-bold bg-emerald-500 text-white rounded-full">
            {[filters.dateFrom, filters.dateTo, filters.meetingType, filters.tags?.length].filter(Boolean).length}
          </span>
        )}
      </button>

      {hasActiveFilters && (
        <button
          type="button"
          onClick={handleClearFilters}
          className="text-xs sm:text-sm font-medium text-slate-500 hover:text-red-400 active:text-red-500 transition-colors touch-manipulation min-h-[44px] px-2 sm:px-3"
        >
          Reset
        </button>
      )}
    </div>
  );
}

function FilterPanelExpanded({ filters, onFilterChange }) {
  const dateFromRef = useRef(null);
  const dateToRef = useRef(null);

  const handleDateFromChange = (e) => {
    onFilterChange({ ...filters, dateFrom: e.target.value || null });
  };

  const handleDateToChange = (e) => {
    onFilterChange({ ...filters, dateTo: e.target.value || null });
  };

  const handleMeetingTypeChange = (e) => {
    onFilterChange({ ...filters, meetingType: e.target.value || null });
  };

  const handleTagsChange = (e) => {
    const tagsValue = e.target.value;
    const tagsArray = tagsValue
      .split(",")
      .map((tag) => tag.trim().toLowerCase())
      .filter((tag) => tag.length > 0);
    onFilterChange({ ...filters, tags: tagsArray });
  };

  const openDateFromPicker = () => {
    if (dateFromRef.current) {
      dateFromRef.current.showPicker?.();
      dateFromRef.current.focus();
    }
  };

  const openDateToPicker = () => {
    if (dateToRef.current) {
      dateToRef.current.showPicker?.();
      dateToRef.current.focus();
    }
  };

  return (
    <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 p-3 sm:p-4 bg-slate-800/40 border border-slate-700/50 rounded-xl">
      <div className="space-y-1.5">
        <label className="block text-xs sm:text-sm font-medium text-slate-400">From Date</label>
        <div className="relative">
          <input
            ref={dateFromRef}
            type="date"
            value={filters.dateFrom || ""}
            onChange={handleDateFromChange}
            className="date-input-custom-icon w-full px-3 py-2.5 sm:py-2.5 pr-10 sm:pr-12 bg-slate-900/50 border border-slate-700/60 rounded-lg text-slate-100 text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/40 transition-all touch-manipulation"
          />
          <button
            type="button"
            onClick={openDateFromPicker}
            className="absolute right-2 sm:right-3 top-1/2 -translate-y-1/2 text-slate-300 hover:text-emerald-400 active:text-emerald-500 transition-colors cursor-pointer z-10 p-1.5 sm:p-1 touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Open calendar"
          >
            <svg
              className="w-5 h-5 sm:w-5 sm:h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </button>
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs sm:text-sm font-medium text-slate-400">To Date</label>
        <div className="relative">
          <input
            ref={dateToRef}
            type="date"
            value={filters.dateTo || ""}
            onChange={handleDateToChange}
            className="date-input-custom-icon w-full px-3 py-2.5 sm:py-2.5 pr-10 sm:pr-12 bg-slate-900/50 border border-slate-700/60 rounded-lg text-slate-100 text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/40 transition-all touch-manipulation"
          />
          <button
            type="button"
            onClick={openDateToPicker}
            className="absolute right-2 sm:right-3 top-1/2 -translate-y-1/2 text-slate-300 hover:text-emerald-400 active:text-emerald-500 transition-colors cursor-pointer z-10 p-1.5 sm:p-1 touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Open calendar"
          >
            <svg
              className="w-5 h-5 sm:w-5 sm:h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </button>
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs sm:text-sm font-medium text-slate-400">Meeting Type</label>
        <select
          value={filters.meetingType || ""}
          onChange={handleMeetingTypeChange}
          className="w-full px-3 py-2.5 sm:py-2.5 bg-slate-900/50 border border-slate-700/60 rounded-lg text-slate-100 text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/40 transition-all touch-manipulation"
        >
          {MEETING_TYPES.map((type) => (
            <option key={type.value} value={type.value} className="bg-slate-800">
              {type.label}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs sm:text-sm font-medium text-slate-400">Filter by Tags</label>
        <input
          type="text"
          value={(filters.tags || []).join(", ")}
          onChange={handleTagsChange}
          placeholder="urgent, follow-up"
          className="w-full px-3 py-2.5 sm:py-2.5 bg-slate-900/50 border border-slate-700/60 rounded-lg text-slate-100 text-sm sm:text-base placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/40 transition-all touch-manipulation"
        />
      </div>
    </div>
  );
}

export { FilterPanelExpanded };
export default FilterPanel;
