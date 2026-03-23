const sortSummariesByCreatedAtDesc = (items) => {
  if (!Array.isArray(items)) {
    return [];
  }
  return [...items].sort((a, b) => {
    const ta = new Date(a?.created_at || 0).getTime();
    const tb = new Date(b?.created_at || 0).getTime();
    return tb - ta;
  });
};

export { sortSummariesByCreatedAtDesc };
