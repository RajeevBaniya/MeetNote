import express from 'express';
import { generateMeetingSummary } from '../services/groq.js';
import { saveSummary } from '../services/summaries.js';

const router = express.Router();

router.post('/generate', async (req, res) => {
  const {
    transcript,
    instruction,
    title,
    meetingTitle,
    meetingDate,
    meetingType,
    participants,
    location,
    tags,
    extractStructured,
    meetingId,
    persist,
  } = req.body;

  if (!transcript) {
    return res.status(400).json({ error: 'Transcript is required' });
  }

  if (!instruction) {
    return res.status(400).json({ error: 'Instruction is required' });
  }

  try {
    const shouldExtract = extractStructured !== false;
    const { summary, structured } = await generateMeetingSummary(
      transcript,
      instruction,
      shouldExtract
    );

    let saved = null;
    if (persist === false) {
      saved = null;
    } else {
      saved = await saveSummary({
        transcript,
        summary,
        instruction,
        title: title ?? null,
        meetingTitle: meetingTitle ?? null,
        meetingDate: meetingDate ? new Date(meetingDate) : null,
        meetingType: meetingType ?? null,
        participants: participants ?? [],
        location: location ?? null,
        tags: tags ?? [],
        actionItems: structured?.actionItems ?? [],
        decisions: structured?.decisions ?? [],
        deadlines: structured?.deadlines ?? [],
        extractedParticipants: structured?.participants ?? [],
        meetingId: meetingId ?? null,
        userId: req.user.id,
      });
    }

    res.json({
      success: true,
      summary,
      structured,
      savedId: saved?.id ?? null,
    });
  } catch (error) {
    console.error('Summary generation error:', error.message);
    res.status(500).json({
      error: 'Failed to generate summary',
      details: error.message,
    });
  }
});

export default router;
