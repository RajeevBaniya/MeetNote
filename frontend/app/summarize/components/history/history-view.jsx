"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { apiFetch } from "../../lib/api";
import ConfirmDialog from "../ui/confirm-dialog";
import FilterPanel, { FilterPanelExpanded } from "./filter-panel";
import SortDropdown from "./sort-dropdown";
import HistoryList from "./history-list";

const HistoryView = ({ onSelectSummary, uploadOnly = false }) => {
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

  const fetchSummaries = useCallback(
    async (params = {}) => {
      try {
        setIsLoading(true);
        setError(null);

        const queryParams = new URLSearchParams();
        if (params.dateFrom) queryParams.append("dateFrom", params.dateFrom);
        if (params.dateTo) queryParams.append("dateTo", params.dateTo);
        if (params.meetingType) queryParams.append("meetingType", params.meetingType);
        if (params.tags && params.tags.length > 0) {
          params.tags.forEach((tag) => queryParams.append("tags", tag));
        }
        if (params.sortBy) queryParams.append("sortBy", params.sortBy);
        if (params.sortOrder) queryParams.append("sortOrder", params.sortOrder);
        if (uploadOnly) queryParams.append("uploadOnly", "true");

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
    },
    [uploadOnly]
  );

  useEffect(() => {
    fetchSummaries({ ...filters, ...sort });
  }, [filters, sort, fetchSummaries]);

  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters);
  }, []);

  const handleSortChange = useCallback((newSort) => {
    setSort(newSort);
  }, []);

  const requestDelete = useCallback((id) => {
    setPendingDeleteId(id);
  }, []);

  const confirmDelete = useCallback(async () => {
    if (!pendingDeleteId) return;
    try {
      await apiFetch(`/api/summaries/${pendingDeleteId}`, {
        method: "DELETE",
      });
      setSummaries((prev) => prev.filter((s) => s.id !== pendingDeleteId));
    } catch (err) {
      console.error("Error deleting summary:", err);
      alert("Failed to delete summary");
    } finally {
      setPendingDeleteId(null);
    }
  }, [pendingDeleteId]);

  const handleSelect = useCallback(
    (summary) => {
      onSelectSummary?.(summary);
    },
    [onSelectSummary]
  );

  const hasFilters = useMemo(
    () =>
      Boolean(
        filters.dateFrom ||
          filters.dateTo ||
          filters.meetingType ||
          (filters.tags && filters.tags.length > 0)
      ),
    [filters]
  );

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
            onToggle={() => setIsFilterExpanded((v) => !v)}
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

      <HistoryList
        summaries={summaries}
        hasFilters={hasFilters}
        onSelect={handleSelect}
        onRequestDelete={requestDelete}
      />

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
};

export default HistoryView;
