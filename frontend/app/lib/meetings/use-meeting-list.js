"use client";

import { useEffect, useState } from "react";

import { addSummariesToMeetings } from "@/app/lib/meetings/summaries-for-meetings";
import { getMyMeetings } from "@/app/lib/meetings/get-my-meetings";

const filterExcluded = (list, excludeIds) => {
  if (!excludeIds || excludeIds.length === 0) return list;
  const exclude = new Set(excludeIds.map(String));
  return list.filter((m) => !exclude.has(String(m.id)));
};

const useMeetingList = (jwt, apiUrl, excludeMeetingIds) => {
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [summariesLoading, setSummariesLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!jwt || !apiUrl) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSummariesLoading(false);
    (async () => {
      try {
        const list = await getMyMeetings(apiUrl, jwt);
        if (cancelled) return;
        const filtered = filterExcluded(list, excludeMeetingIds);
        const base = filtered.map((m) => ({
          ...m,
          has_summary: false,
        }));
        setMeetings(base);
        setLoading(false);
        setSummariesLoading(true);
        const withSummaries = await addSummariesToMeetings(base);
        if (!cancelled) {
          setMeetings(withSummaries);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to load meetings");
          setMeetings([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          setSummariesLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [jwt, apiUrl, excludeMeetingIds]);

  return { meetings, loading, summariesLoading, error };
};

export { useMeetingList };
