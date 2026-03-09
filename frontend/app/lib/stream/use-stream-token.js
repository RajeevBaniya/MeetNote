import { useEffect, useState, useRef } from "react";
import { useAuth } from "@/app/lib/auth/use-auth";

const POLL_INTERVAL_MS = 3000;

function buildUrl(baseUrl, meetingId) {
  const base = (baseUrl || "").replace(/\/$/, "");
  return `${base}/meetings/${meetingId}/stream-token`;
}

export const useStreamTokenFromBackend = (meetingId, jwtProp, displayName, passcode, enabled = true) => {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState("loading");
  const [expiresInSeconds, setExpiresInSeconds] = useState(null);
  const timeoutRef = useRef(null);
  const mountedRef = useRef(true);
  const { jwt, refreshAccessToken } = useAuth();

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  useEffect(() => {
    const activeJwt = jwtProp || jwt;

    if (!enabled || !meetingId || !activeJwt) {
      if (!activeJwt && meetingId) {
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

      const send = async (tokenToUse) =>
        fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${tokenToUse}`,
          },
          body: JSON.stringify({
            display_name: displayName != null ? String(displayName).trim() : "",
            passcode: passcode != null ? String(passcode).trim() : undefined,
          }),
        });

      let res = await send(activeJwt);

      if (res.status === 401) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          res = await send(refreshed);
        }
      }

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

      if (res.status === 429) {
        setError({
          status: 429,
          code: "rate_limit_exceeded",
        });
        setStatus("error");
        return;
      }

      if (res.status === 409) {
        const text = await res.text();
        let message = "Meeting has not been started by host yet.";
        try {
          const parsed = JSON.parse(text);
          if (parsed && typeof parsed.detail === "string" && parsed.detail.trim()) {
            message = parsed.detail;
          }
        } catch {
          if (text && text.trim()) {
            message = text;
          }
        }
        setError(message);
        setStatus("host_not_started");
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
        if (detail.includes("scheduled") && detail.includes("has not started")) {
          setError("This meeting is scheduled and has not started yet.");
          setStatus("scheduled");
          return;
        }
        setError(text || "You are not allowed to join this meeting.");
        setStatus("error");
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
  }, [meetingId, jwtProp, jwt, displayName, passcode, enabled, refreshAccessToken]);

  return { token, user, error, status, expiresInSeconds };
};
