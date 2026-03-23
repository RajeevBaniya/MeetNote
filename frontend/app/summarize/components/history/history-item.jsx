"use client";

import { useCallback } from "react";

import {
  formatDate,
  getDisplayTitle,
  getMeetingDate,
  getActionItemsCount,
} from "../../lib/history-helpers";
import ExportButton from "../summary/export-button";
import { Button } from "../ui/button";
import {
  ActionItemsCount,
  MeetingTypeBadge,
  ParticipantsBadge,
  TagsBadge,
} from "./history-badges";

const HistoryItem = ({ summary, onSelect, onRequestDelete }) => {
  const displayTitle = getDisplayTitle(summary);
  const meetingDate = getMeetingDate(summary);
  const createdDate = formatDate(summary.created_at);
  const actionCount = getActionItemsCount(summary);

  const handleClick = useCallback(() => {
    onSelect?.(summary);
  }, [onSelect, summary]);

  const handleOpenClick = useCallback(
    (e) => {
      e.stopPropagation();
      onSelect?.(summary);
    },
    [onSelect, summary]
  );

  const handleRemoveClick = useCallback(
    (e) => {
      e.stopPropagation();
      onRequestDelete?.(summary.id);
    },
    [onRequestDelete, summary.id]
  );

  return (
    <div
      role="button"
      tabIndex={0}
      className="history-item group border border-slate-700/40 rounded-xl p-4 pl-5 hover:border-emerald-500/40 hover:bg-slate-800/40 transition-all duration-200 cursor-pointer"
      onClick={handleClick}
      onKeyDown={(e) => e.key === "Enter" && handleClick()}
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
              &quot;{summary.instruction}&quot;
            </p>
          )}

          {createdDate && !meetingDate && (
            <p className="text-xs text-slate-600 mt-2">Created {createdDate}</p>
          )}
        </div>

        <div className="flex flex-col gap-2 shrink-0 opacity-60 group-hover:opacity-100 transition-opacity">
          <Button
            variant="outline"
            size="sm"
            onClick={handleOpenClick}
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
            onClick={handleRemoveClick}
          >
            Remove
          </Button>
        </div>
      </div>
    </div>
  );
};

export default HistoryItem;
