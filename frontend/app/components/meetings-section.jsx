"use client";

import MeetingRow from "@/app/components/meeting-row";
import { useMeetingList } from "@/app/lib/meetings/use-meeting-list";

const formatWhen = (iso) => {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
};

const MeetingsSection = ({
  jwt,
  apiUrl,
  onShareMeeting,
  onCopyMeeting,
  lastCopiedId,
  excludeMeetingIds,
}) => {
  const { meetings, loading, summariesLoading, error } = useMeetingList(
    jwt,
    apiUrl,
    excludeMeetingIds,
  );
  const base = apiUrl ? apiUrl.replace(/\/$/, "") : "";

  if (loading) {
    return (
      <section>
        <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
          All meetings
        </h2>
        <p className="mb-4 text-lg font-medium text-slate-100">
          Host or participant
        </p>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
            <p className="mt-3 text-sm text-slate-500">Loading meetings…</p>
          </div>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section>
        <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
          All meetings
        </h2>
        <p className="mb-4 text-lg font-medium text-slate-100">
          Host or participant
        </p>
        <div className="rounded-xl border border-red-500/40 bg-red-900/20 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      </section>
    );
  }

  return (
    <section>
      <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
        All meetings
      </h2>
      <p className="mb-4 text-lg font-medium text-slate-100">
        Everything you hosted or joined
      </p>
      <p className="mb-4 text-xs text-slate-500">
        Rows above list meetings from your host dashboard. Here you also see
        meetings you joined as a participant (duplicates are hidden).
      </p>
      {meetings.length === 0 ? (
        <div className="rounded-xl border border-slate-700/50 border-dashed bg-slate-800/30 px-5 py-8 text-center">
          <p className="text-sm text-slate-500">No meetings yet</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {meetings.map((meeting) => {
            const when = formatWhen(meeting.created_at);
            const icsHref =
              base && meeting.scheduled_start_at
                ? `${base}/meetings/${meeting.id}/ics`
                : null;
            const isActive = Boolean(meeting.is_active);
            const primaryHref = isActive
              ? `/meeting/${meeting.id}`
              : `/summarize?meetingId=${encodeURIComponent(meeting.id)}`;
            const primaryLabel = isActive ? "Join" : "View summary";
            return (
              <li key={meeting.id}>
                <MeetingRow
                  title={meeting.title}
                  subtitle={when || null}
                  statusLabel={isActive ? "Active" : "Ended"}
                  participantCount={meeting.participant_count}
                  showHasSummary={
                    !summariesLoading && !isActive && meeting.has_summary
                  }
                  primaryHref={primaryHref}
                  primaryLabel={primaryLabel}
                >
                  {onShareMeeting ? (
                    <button
                      type="button"
                      onClick={() => onShareMeeting(meeting.id)}
                      className="inline-flex shrink-0 items-center justify-center rounded-lg bg-slate-600 px-4 py-2.5 text-sm font-semibold text-slate-100 transition hover:bg-slate-500"
                    >
                      Share
                    </button>
                  ) : null}
                  {onCopyMeeting ? (
                    <button
                      type="button"
                      onClick={() => onCopyMeeting(meeting.id)}
                      className="inline-flex shrink-0 items-center justify-center rounded-lg bg-slate-600 px-4 py-2.5 text-sm font-semibold text-slate-100 transition hover:bg-slate-500"
                    >
                      {lastCopiedId === meeting.id
                        ? "Copied to clipboard"
                        : "Copy"}
                    </button>
                  ) : null}
                  {icsHref ? (
                    <a
                      href={icsHref}
                      className="inline-flex shrink-0 items-center justify-center rounded-lg bg-slate-600 px-4 py-2.5 text-sm font-semibold text-slate-100 transition hover:bg-slate-500"
                    >
                      Download ICS
                    </a>
                  ) : null}
                </MeetingRow>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
};

export default MeetingsSection;
