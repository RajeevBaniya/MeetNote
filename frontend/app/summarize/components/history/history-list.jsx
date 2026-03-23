"use client";

import HistoryItem from "./history-item";

const EmptyState = ({ hasFilters }) => (
  <div className="empty-state">
    <div className="empty-state-icon">
      <svg
        className="w-8 h-8"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.5"
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
    </div>
    <p className="empty-state-text">
      {hasFilters
        ? "No summaries match your current filters. Try adjusting your criteria."
        : "Your meeting summaries will appear here once you create your first one."}
    </p>
  </div>
);

const HistoryList = ({ summaries, hasFilters, onSelect, onRequestDelete }) => {
  if (summaries.length === 0) {
    return <EmptyState hasFilters={hasFilters} />;
  }

  return (
    <div className="space-y-4">
      {summaries.map((summary) => (
        <HistoryItem
          key={summary.id}
          summary={summary}
          onSelect={onSelect}
          onRequestDelete={onRequestDelete}
        />
      ))}
    </div>
  );
};

export default HistoryList;
