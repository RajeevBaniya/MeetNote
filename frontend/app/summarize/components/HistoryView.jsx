"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { apiFetch } from "../lib/api";
import { Button } from "./ui/button";
import ConfirmDialog from "./ui/confirm-dialog";
import FilterPanel, { FilterPanelExpanded } from "./FilterPanel";
import SortDropdown from "./SortDropdown";
import ExportButton from "./ExportButton";

const MEETING_TYPE_LABELS = {
  team: "Team Meeting",
  "one-on-one": "1-on-1",
  client: "Client Meeting",
  standup: "Standup",
  "project-review": "Project Review",
  brainstorm: "Brainstorming",
  interview: "Interview",
  training: "Training",
  other: "Other",
};

function formatDate(dateString) {
  if (!dateString) return null;
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return null;
  return date.toLocaleString();
}

function MeetingTypeBadge({ type }) {
  if (!type) return null;
  const label = MEETING_TYPE_LABELS[type] || type;
  return <span className="meeting-type-badge">{label}</span>;
}

function ParticipantsBadge({ participants }) {
  if (!participants || participants.length === 0) return null;
  const displayCount = Math.min(participants.length, 2);
  const remaining = participants.length - displayCount;

  return (
    <span className="inline-flex items-center gap-1 text-xs text-slate-400">
      <svg
        className="w-3 h-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
        />
      </svg>
      {participants.slice(0, displayCount).join(", ")}
      {remaining > 0 && ` +${remaining}`}
    </span>
  );
}

function ActionItemsCount({ count }) {
  if (!count || count === 0) return null;
  return (
    <span className="action-indicator">
      <svg
        className="w-3 h-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
        />
      </svg>
      {count} action{count !== 1 ? "s" : ""}
    </span>
  );
}

function TagsBadge({ tags }) {
  if (!tags || tags.length === 0) return null;
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {tags.slice(0, 3).map((tag) => (
        <span key={tag} className="tag-chip">
          #{tag}
        </span>
      ))}
      {tags.length > 3 && (
        <span className="text-xs text-slate-500 ml-1">+{tags.length - 3}</span>
      )}
    </div>
  );
}

function HistoryView({ onSelectSummary, uploadOnly = false }) {
  const [summaries, setSummaries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pendingDeleteId, setPendingDeleteId] = useState(null);

  const [filters, setFilters] = useState({
    dateFrom: null,
    dateTo: null,
    meetingType: null,
    tags: [],
  });
  const [sort, setSort] = useState({
    sortBy: "created_at",
    sortOrder: "desc",
  });
  const [isFilterExpanded, setIsFilterExpanded] = useState(false);

  const fetchSummaries = useCallback(async (params = {}) => {
    try {
      setIsLoading(true);
      setError(null);

      const queryParams = new URLSearchParams();

      if (params.dateFrom) {
        queryParams.append("dateFrom", params.dateFrom);
      }
      if (params.dateTo) {
        queryParams.append("dateTo", params.dateTo);
      }
      if (params.meetingType) {
        queryParams.append("meetingType", params.meetingType);
      }
      if (params.tags && params.tags.length > 0) {
        params.tags.forEach((tag) => queryParams.append("tags", tag));
      }
      if (params.sortBy) {
        queryParams.append("sortBy", params.sortBy);
      }
      if (params.sortOrder) {
        queryParams.append("sortOrder", params.sortOrder);
      }
      if (uploadOnly) {
        queryParams.append("uploadOnly", "true");
      }

      const queryString = queryParams.toString();
      const url = queryString
        ? `/api/summaries?${queryString}`
        : "/api/summaries";

      const response = await apiFetch(url);
      setSummaries(response.items || []);
    } catch (err) {
      console.error("Error fetching summaries:", err);
      setError("Failed to load your summary history");
    } finally {
      setIsLoading(false);
    }
  }, [uploadOnly]);

  useEffect(() => {
    fetchSummaries({
      ...filters,
      ...sort,
    });
  }, [filters, sort, fetchSummaries]);

  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters);
  }, []);

  const handleSortChange = useCallback((newSort) => {
    setSort(newSort);
  }, []);

  const requestDelete = (id) => {
    setPendingDeleteId(id);
  };

  const confirmDelete = async () => {
    if (!pendingDeleteId) return;
    try {
      await apiFetch(`/api/summaries/${pendingDeleteId}`, {
        method: "DELETE",
      });
      setSummaries(summaries.filter((s) => s.id !== pendingDeleteId));
    } catch (err) {
      console.error("Error deleting summary:", err);
      alert("Failed to delete summary");
    } finally {
      setPendingDeleteId(null);
    }
  };

  const handleSelect = (summary) => {
    if (onSelectSummary) {
      onSelectSummary(summary);
    }
  };

  const getDisplayTitle = (summary) => {
    if (summary.meeting_title) return summary.meeting_title;
    if (summary.title) {
      const titleDate = new Date(summary.title);
      if (!isNaN(titleDate.getTime())) {
        return formatDate(summary.title);
      }
      return summary.title;
    }
    return formatDate(summary.created_at) || "Untitled";
  };

  const getMeetingDate = (summary) => {
    if (summary.meeting_date) return formatDate(summary.meeting_date);
    return null;
  };

  const getActionItemsCount = (summary) => {
    if (Array.isArray(summary.action_items)) {
      return summary.action_items.length;
    }
    return 0;
  };

  const hasFilters = useMemo(() => {
    return (
      filters.dateFrom ||
      filters.dateTo ||
      filters.meetingType ||
      (filters.tags && filters.tags.length > 0)
    );
  }, [filters]);

  if (isLoading) {
    return (
      <div className="card">
        <h2 className="section-title mb-4">Summary History</h2>
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2 className="section-title mb-4">Summary History</h2>
        <div className="p-4 bg-red-500/15 border border-red-500/30 rounded-lg">
          <p className="text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="section-title mb-4">Summary History</h2>

      <div className="mb-5 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <FilterPanel
            filters={filters}
            onFilterChange={handleFilterChange}
            isExpanded={isFilterExpanded}
            onToggle={() => setIsFilterExpanded(!isFilterExpanded)}
          />
          <SortDropdown
            sortBy={sort.sortBy}
            sortOrder={sort.sortOrder}
            onSortChange={handleSortChange}
          />
        </div>
        {isFilterExpanded && (
          <FilterPanelExpanded
            filters={filters}
            onFilterChange={handleFilterChange}
          />
        )}
      </div>

      {summaries.length === 0 ? (
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
      ) : (
        <div className="space-y-4">
          {summaries.map((summary) => {
            const displayTitle = getDisplayTitle(summary);
            const meetingDate = getMeetingDate(summary);
            const createdDate = formatDate(summary.created_at);
            const actionCount = getActionItemsCount(summary);

            return (
              <div
                key={summary.id}
                className="history-item group border border-slate-700/40 rounded-xl p-4 pl-5 hover:border-emerald-500/40 hover:bg-slate-800/40 transition-all duration-200 cursor-pointer"
                onClick={() => handleSelect(summary)}
              >
                <div className="flex justify-between items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <h3 className="font-semibold text-slate-100 truncate group-hover:text-emerald-300 transition-colors">
                        {displayTitle}
                      </h3>
                      <MeetingTypeBadge type={summary.meeting_type} />
                    </div>

                    <div className="flex items-center gap-3 mt-2.5 flex-wrap">
                      {meetingDate && (
                        <span className="inline-flex items-center gap-1.5 text-sm text-slate-400">
                          <svg
                            className="w-3.5 h-3.5 text-slate-500"
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
                          {meetingDate}
                        </span>
                      )}
                      <ParticipantsBadge participants={summary.participants} />
                      <ActionItemsCount count={actionCount} />
                      <TagsBadge tags={summary.tags} />
                    </div>

                    {summary.instruction && (
                      <p className="text-sm text-slate-500 mt-2.5 line-clamp-1 italic">
                        "{summary.instruction}"
                      </p>
                    )}

                    {createdDate && !meetingDate && (
                      <p className="text-xs text-slate-600 mt-2">
                        Created {createdDate}
                      </p>
                    )}
                  </div>

                  <div className="flex flex-col gap-2 flex-shrink-0 opacity-60 group-hover:opacity-100 transition-opacity">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelect(summary);
                      }}
                      className="w-full text-xs"
                    >
                      Open
                    </Button>
                    <div className="flex gap-1">
                      <ExportButton
                        summaryId={summary.id}
                        fileName={
                          summary.meeting_title
                            ? `${summary.meeting_title}.pdf`
                            : undefined
                        }
                        variant="outline"
                      />
                    </div>
                    <Button
                      variant="destructive"
                      size="sm"
                      className="w-full text-xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        requestDelete(summary.id);
                      }}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <ConfirmDialog
        open={!!pendingDeleteId}
        title="Delete summary?"
        description="This action cannot be undone. The summary will be permanently removed."
        confirmText="Delete"
        onConfirm={confirmDelete}
        onCancel={() => setPendingDeleteId(null)}
        confirmVariant="destructive"
      />
    </div>
  );
}

export default HistoryView;
