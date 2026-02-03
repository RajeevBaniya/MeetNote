import { useEffect, useState, useRef } from "react";

const POLL_INTERVAL_MS = 3000;

function buildUrl(baseUrl, meetingId) {
  const base = (baseUrl || "").replace(/\/$/, "");
  return `${base}/meetings/${meetingId}/stream-token`;
}

export function useStreamTokenFromBackend(meetingId, jwt, displayName) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState("loading");
  const timeoutRef = useRef(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  useEffect(() => {
    if (!meetingId || !jwt) {
      if (!jwt && meetingId) {
        setError("Not authenticated");
        setStatus("error");
      } else {
        setStatus("loading");
      }
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      setError("NEXT_PUBLIC_API_URL not set");
      setStatus("error");
      return;
    }

    let cancelled = false;

    const fetchToken = async () => {
      const url = buildUrl(apiUrl, meetingId);
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${jwt}`,
        },
      });

      if (cancelled || !mountedRef.current) return;

      if (res.status === 200) {
        const data = await res.json();
        setToken(data.token);
        setUser({
          id: data.user_id,
          name: displayName || data.user_id,
        });
        setError(null);
        setStatus("ready");
        return;
      }

      if (res.status === 403) {
        setStatus("waiting_approval");
        setError(null);
        timeoutRef.current = setTimeout(fetchToken, POLL_INTERVAL_MS);
        return;
      }

      const text = await res.text();
      setError(text || `Request failed (${res.status})`);
      setStatus("error");
    };

    setStatus("loading");
    setError(null);
    fetchToken();

    return () => {
      cancelled = true;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [meetingId, jwt, displayName]);

  return { token, user, error, status };
}
