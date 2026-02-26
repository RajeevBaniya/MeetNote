import { google } from 'googleapis';
import dotenv from 'dotenv';

dotenv.config();

const getGmailClient = () => {
  const {
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REFRESH_TOKEN,
  } = process.env;

  if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET || !GOOGLE_REFRESH_TOKEN) {
    throw new Error('Gmail API credentials not configured');
  }

  const oauth2Client = new google.auth.OAuth2(
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET
  );

  oauth2Client.setCredentials({
    refresh_token: GOOGLE_REFRESH_TOKEN,
  });

  return google.gmail({ version: 'v1', auth: oauth2Client });
};

const createEmailMessage = (to, from, subject, htmlContent, replyTo = null) => {
  const headers = [
    `To: ${to}`,
    `From: ${from}`,
    `Subject: ${subject}`,
    `Content-Type: text/html; charset=utf-8`,
  ];

  if (replyTo) {
    headers.push(`Reply-To: ${replyTo}`);
  }

  const email = [
    headers.join('\r\n'),
    '',
    htmlContent,
  ].join('\r\n');

  return Buffer.from(email)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
};

export const sendSummaryEmail = async (
  recipients,
  summary,
  subject = 'Meeting Summary',
  replyToEmail = null
) => {
  const { GMAIL_USER_EMAIL } = process.env;

  if (!GMAIL_USER_EMAIL) {
    throw new Error('GMAIL_USER_EMAIL not configured');
  }

  const gmail = getGmailClient();

  const emailContent = `
<h2>Meeting Summary</h2>
<div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; font-family: Arial, sans-serif;">
  <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">${summary}</pre>
</div>
  `;

  const results = [];

  for (const recipient of recipients) {
    try {
      const rawMessage = createEmailMessage(
        recipient,
        GMAIL_USER_EMAIL,
        subject,
        emailContent,
        replyToEmail
      );

      const response = await gmail.users.messages.send({
        userId: 'me',
        requestBody: {
          raw: rawMessage,
        },
      });

      results.push({
        recipient,
        success: true,
        messageId: response.data.id,
      });
    } catch (error) {
      console.error(`Email sending error for ${recipient}:`, error);
      results.push({
        recipient,
        success: false,
        error: error.message,
      });
    }
  }

  const failedRecipients = results.filter((r) => !r.success);

  if (failedRecipients.length > 0) {
    const errorMessage = `Failed to send to: ${failedRecipients.map((r) => r.recipient).join(', ')}`;
    throw new Error(errorMessage);
  }

  return results;
};
