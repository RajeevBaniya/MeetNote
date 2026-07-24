"use client";

import MeetingInsightsBase from "../../meeting-insights";

const MeetingInsights = ({ meetingId, jwt, meeting }) => {
  return (
    <MeetingInsightsBase
      meetingId={meetingId}
      jwt={jwt}
      meeting={meeting}
    />
  );
};

export default MeetingInsights;
