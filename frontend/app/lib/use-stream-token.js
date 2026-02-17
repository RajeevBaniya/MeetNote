import { useEffect, useState, useRef } from "react";

const POLL_INTERVAL_MS = 3000;

function buildUrl(baseUrl, meetingId) {
  const base = (baseUrl || "").replace(/\/$/, "");
  return `${base}/meetings/${meetingId}/stream-token`;
}

export function useStreamTokenFromBackend(meetingId, jwt, displayName, passcode, enabled = true) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState("loading");
  const [expiresInSeconds, setExpiresInSeconds] = useState(null);
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
    if (!enabled || !meetingId || !jwt) {
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
        body: JSON.stringify({
          display_name: displayName != null ? String(displayName).trim() : "",
          passcode: passcode != null ? String(passcode).trim() : undefined,
        }),
      });

      if (cancelled || !mountedRef.current) return;

      if (res.status === 200) {
        const data = await res.json();
        setToken(data.token);
        setUser({
          id: data.user_id,
          name: displayName || data.user_id,
        });
        setExpiresInSeconds(
          typeof data.expires_in_seconds === "number" ? data.expires_in_seconds : null
        );
        setError(null);
        setStatus("ready");
        return;
      }

      if (res.status === 403) {
        const text = await res.text();
        let detail = "";
        try {
          const parsed = JSON.parse(text);
          detail = (parsed.detail || "").toLowerCase();
        } catch {
          detail = text.toLowerCase();
        }
        if (detail.includes("removed")) {
          setError("You were removed from this meeting");
          setStatus("error");
          return;
        }
         if (detail.includes("passcode required")) {
          setError("Passcode required");
          setStatus("error");
          return;
        }
        if (detail.includes("incorrect passcode")) {
          setError("Incorrect passcode");
          setStatus("error");
          return;
        }
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
  }, [meetingId, jwt, displayName, passcode, enabled]);

  return { token, user, error, status, expiresInSeconds };
}
