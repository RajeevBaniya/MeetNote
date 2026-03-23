const applySummaryItemToState = (item, {
  setTranscript,
  setSummary,
  setStructured,
  setCurrentSummaryId,
}) => {
  setTranscript(item.transcript ?? "");
  setSummary(item.summary ?? "");
  setStructured({
    actionItems: item.action_items || [],
    decisions: item.decisions || [],
    deadlines: item.deadlines || [],
    participants: item.extracted_participants || [],
  });
  if (setCurrentSummaryId && item.id) {
    setCurrentSummaryId(item.id);
  }
};

export { applySummaryItemToState };
