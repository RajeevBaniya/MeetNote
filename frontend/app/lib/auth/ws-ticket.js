import { getToken } from "./token-store";

export const fetchWsTicket = async () => {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const token = getToken();
    const res = await fetch(`${baseUrl}/auth/ws-ticket`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      return null;
    }
    const data = await res.json();
    return data.ticket || null;
  } catch (err) {
    console.error("fetchWsTicket error", err);
    return null;
  }
};
