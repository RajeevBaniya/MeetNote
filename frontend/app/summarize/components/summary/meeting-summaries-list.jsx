"use client";

const formatMeetingDateLabel = (meetingDate) => {
  if (!meetingDate) {
    return null;
  }
  return new Date(meetingDate).toLocaleDateString();
};

const MeetingSummaryListItem = ({ item, onSelectSummary }) => {
  const handleClick = () => {
    onSelectSummary?.(item);
  };

  const dateLabel = formatMeetingDateLabel(item.meeting_date);

  return (
    <li>
      <button
        type="button"
        onClick={handleClick}
        className="w-full rounded-lg border border-slate-600/60 bg-slate-800/60 px-3 py-2.5 text-left text-sm text-slate-200 transition hover:border-emerald-500/50 hover:bg-slate-700/60"
      >
        <span className="font-medium text-slate-100">
          {item.title || item.meeting_title || "Summary"}
        </span>
        {dateLabel ? (
          <span className="ml-2 text-xs text-slate-500">{dateLabel}</span>
        ) : null}
      </button>
    </li>
  );
};

const MeetingSummariesList = ({ items, loading, onSelectSummary }) => {
  if (loading) {
    return (
      <div className="card mb-4">
        <p className="text-sm text-slate-400">Loading meeting summaries…</p>
      </div>
    );
  }

  if (!Array.isArray(items) || items.length === 0) {
    return null;
  }

  return (
    <div className="card mb-4">
      <h2 className="section-title mb-3">Summaries for this meeting</h2>
      <ul className="space-y-2">
        {items.map((item) => (
          <MeetingSummaryListItem
            key={item.id}
            item={item}
            onSelectSummary={onSelectSummary}
          />
        ))}
      </ul>
    </div>
  );
};

export default MeetingSummariesList;
