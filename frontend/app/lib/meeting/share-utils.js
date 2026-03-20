/**
 * @param { { title?: string | null; join_code?: string | null; passcode?: string | null; join_url?: string | null } } info
 * @returns {string}
 */
const buildShareMessage = (info) => {
  if (!info) return "";
  const lines = [
    `Meeting: ${info.title || "Meeting"}`,
    `Meeting ID: ${info.join_code ?? ""}`,
    `Passcode: ${info.passcode ?? ""}`,
    "",
    "Join here:",
    info.join_url ?? "",
  ];
  return lines.join("\n");
};

/**
 * @param {string} text
 * @returns {Promise<void>}
 */
const copyMeetingShare = (text) => {
  if (!text) return Promise.resolve();
  return navigator.clipboard.writeText(text);
};

/**
 * @param { { title?: string | null; join_code?: string | null; passcode?: string | null; join_url?: string | null } } info
 * @param { (text: string) => Promise<void> } [fallbackCopy]
 * @returns {Promise<void>}
 */
const nativeShareMeeting = async (info, fallbackCopy = copyMeetingShare) => {
  if (!info) return;
  const text = buildShareMessage(info);
  if (typeof navigator.share === "function") {
    try {
      await navigator.share({
        title: info.title || "Meeting",
        text,
      });
    } catch (err) {
      await fallbackCopy(text);
    }
  } else {
    await fallbackCopy(text);
  }
};

export { buildShareMessage, copyMeetingShare, nativeShareMeeting };
