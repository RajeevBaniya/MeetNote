import Link from "next/link";

function MeetingRow({
  title,
  subtitle,
  statusLabel,
  participantCount,
  showHasSummary,
  primaryHref,
  primaryLabel,
  children,
}) {
  return (
    <div className="group flex flex-col gap-3 rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-4 transition hover:border-slate-600 sm:flex-row sm:items-center sm:justify-between sm:px-5 sm:py-4">
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-slate-100">
          {title || "Untitled meeting"}
        </p>
        {subtitle ? (
          <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
        ) : null}
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          {statusLabel ? (
            <span className="rounded-md border border-slate-600/80 px-2 py-0.5 text-slate-400">
              {statusLabel}
            </span>
          ) : null}
          {typeof participantCount === "number" ? (
            <span>{participantCount} participants</span>
          ) : null}
          {showHasSummary ? (
            <span className="text-emerald-400/90">Summary available</span>
          ) : null}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {primaryHref && primaryLabel ? (
          <Link
            href={primaryHref}
            className="inline-flex shrink-0 items-center justify-center rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#020617]"
          >
            {primaryLabel}
          </Link>
        ) : null}
        {children}
      </div>
    </div>
  );
}

export default MeetingRow;
