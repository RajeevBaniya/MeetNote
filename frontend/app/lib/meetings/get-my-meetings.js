const getMyMeetings = async (apiUrl, jwt) => {
  const base = apiUrl.replace(/\/$/, "");
  const res = await fetch(`${base}/meetings/my`, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed (${res.status})`);
  }
  const data = await res.json();
  return Array.isArray(data) ? data : [];
};

export { getMyMeetings };
