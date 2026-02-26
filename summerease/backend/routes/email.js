import express from 'express';
import { sendSummaryEmail } from '../services/email.js';

const router = express.Router();

router.post('/send', async (req, res) => {
  const { recipients, summary, subject, replyToEmail } = req.body;

  if (!recipients || !Array.isArray(recipients) || recipients.length === 0) {
    return res.status(400).json({ error: 'Recipients array is required' });
  }

  if (!summary) {
    return res.status(400).json({ error: 'Summary is required' });
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const invalidEmails = recipients.filter((email) => !emailRegex.test(email));

  if (invalidEmails.length > 0) {
    return res.status(400).json({
      error: 'Invalid email addresses',
      invalid: invalidEmails,
    });
  }

  try {
    const replyTo = replyToEmail || null;
    await sendSummaryEmail(recipients, summary, subject, replyTo);

    res.json({
      success: true,
      message: 'Summary sent successfully',
      sentTo: recipients,
    });
  } catch (error) {
    console.error('Email sending error:', error.message);
    res.status(500).json({
      error: 'Failed to send email',
      details: error.message,
    });
  }
});

export default router;
