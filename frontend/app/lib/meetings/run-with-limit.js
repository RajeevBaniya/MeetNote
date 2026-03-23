const runWithLimit = async (items, limit, fn) => {
  if (!Array.isArray(items) || items.length === 0) {
    return [];
  }
  const results = new Array(items.length);
  let next = 0;
  const cap = Math.max(1, Math.min(limit, items.length));

  const worker = async () => {
    while (true) {
      const i = next;
      next += 1;
      if (i >= items.length) break;
      results[i] = await fn(items[i], i);
    }
  };

  await Promise.all(Array.from({ length: cap }, () => worker()));
  return results;
};

export { runWithLimit };
