const apiFetch = async (path, options = {}) => {
  const baseUrl = process.env.NEXT_PUBLIC_SUMMARY_API_URL || "http://localhost:5000";
  const url = `${baseUrl}${path}`;

  const defaultHeaders = {};
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("meetnote_jwt");
    if (token) {
      defaultHeaders["Authorization"] = `Bearer ${token}`;
    }
  }
  if (options.body && !(options.body instanceof FormData)) {
    defaultHeaders["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorData;
    try {
      errorData = JSON.parse(errorText);
    } catch {
      errorData = { error: errorText || "API request failed" };
    }
    throw new Error(errorData.error || errorData.message || "API request failed");
  }

  return response.json();
};

export { apiFetch };
