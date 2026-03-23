const RECONNECT_DELAYS_MS = [1000, 2000, 5000, 10000, 30000];

const getReconnectDelayMs = (attempt) => {
  const index = Number.isFinite(attempt) ? Math.max(0, attempt) : 0;
  const capped = Math.min(index, RECONNECT_DELAYS_MS.length - 1);
  return RECONNECT_DELAYS_MS[capped];
};

export { getReconnectDelayMs };

