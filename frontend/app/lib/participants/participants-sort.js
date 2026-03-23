const isAssistantParticipant = (participant) => {
  if (!participant) return false;

  const userId = participant.userId || "";
  const name = participant.name || "";

  return userId === "meeting-assistant-bot" ||
         name === "Assistant" ||
         name.toLowerCase().includes("assistant");
};

const compareParticipants = (a, b) => {
  const isAssistantA = isAssistantParticipant(a);
  const isAssistantB = isAssistantParticipant(b);

  if (isAssistantA && !isAssistantB) return -1;
  if (!isAssistantA && isAssistantB) return 1;
  return 0;
};

const sortParticipants = (participants) => {
  const indexed = participants.map((p, index) => ({ participant: p, index }));

  const sorted = indexed.reduce((acc, current) => {
    const insertIndex = acc.findIndex(item =>
      compareParticipants(current.participant, item.participant) < 0
    );

    if (insertIndex === -1) {
      return [...acc, current];
    }

    return [
      ...acc.slice(0, insertIndex),
      current,
      ...acc.slice(insertIndex)
    ];
  }, []);

  return sorted.map(({ participant }) => participant);
};

const filterAssistant = (participants, showAssistant) => {
  if (showAssistant) {
    return participants;
  }

  return participants.filter(p => !isAssistantParticipant(p));
};

export { isAssistantParticipant, sortParticipants, filterAssistant };
