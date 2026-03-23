const MEETING_TYPE_LABELS = {
  team: "Team Meeting",
  "one-on-one": "1-on-1",
  client: "Client Meeting",
  standup: "Standup",
  "project-review": "Project Review",
  brainstorm: "Brainstorming",
  interview: "Interview",
  training: "Training",
  other: "Other",
};

const formatDate = (dateString) => {
  if (!dateString) return null;
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return null;
  return date.toLocaleString();
};

const getDisplayTitle = (summary) => {
  if (summary.meeting_title) return summary.meeting_title;
  if (summary.title) {
    const titleDate = new Date(summary.title);
    if (!isNaN(titleDate.getTime())) {
      return formatDate(summary.title);
    }
    return summary.title;
  }
  return formatDate(summary.created_at) || "Untitled";
};

const getMeetingDate = (summary) => {
  if (summary.meeting_date) return formatDate(summary.meeting_date);
  return null;
};

const getActionItemsCount = (summary) => {
  if (Array.isArray(summary.action_items)) {
    return summary.action_items.length;
  }
  return 0;
};

export {
  MEETING_TYPE_LABELS,
  formatDate,
  getDisplayTitle,
  getMeetingDate,
  getActionItemsCount,
};
