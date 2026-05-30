import express from 'express';
import { generatePDF } from '../services/export/pdfGenerator.js';
import { generateWordDocument } from '../services/export/wordGenerator.js';
import { getSummaryForExport } from '../services/summaries.js';
import { Packer } from 'docx';

const router = express.Router();

router.get('/pdf/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const summary = await getSummaryForExport(id);

    if (!summary) {
      return res.status(404).json({ error: 'Summary not found' });
    }

    const summaryData = {
      meetingTitle: summary.meeting_title,
      meetingDate: summary.meeting_date,
      meetingType: summary.meeting_type,
      participants: summary.participants || [],
      location: summary.location,
      tags: summary.tags || [],
      summary: summary.summary,
      actionItems: summary.action_items || [],
      decisions: summary.decisions || [],
      deadlines: summary.deadlines || [],
      extractedParticipants: summary.extracted_participants || [],
    };

    const pdfBytes = await generatePDF(summaryData);

    if (!pdfBytes || !(pdfBytes instanceof Uint8Array) || pdfBytes.length === 0) {
      return res.status(500).json({
        error: 'Failed to generate PDF',
        details: 'Generated PDF is empty or invalid',
      });
    }

    const fileName = `${summary.meeting_title || 'meeting-notes'}-${id}.pdf`.replace(
      /[^a-z0-9.-]/gi,
      '-'
    );

    const pdfBuffer = Buffer.from(pdfBytes);

    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `attachment; filename="${encodeURIComponent(fileName)}"`);
    res.setHeader('Content-Length', pdfBuffer.length.toString());
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    res.setHeader('X-Content-Type-Options', 'nosniff');

    res.end(pdfBuffer);
  } catch (error) {
    console.error('PDF export error:', error);
    res.status(500).json({
      error: 'Failed to generate PDF',
      details: error.message,
    });
  }
});

router.get('/word/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const summary = await getSummaryForExport(id);

    if (!summary) {
      return res.status(404).json({ error: 'Summary not found' });
    }

    const summaryData = {
      meetingTitle: summary.meeting_title,
      meetingDate: summary.meeting_date,
      meetingType: summary.meeting_type,
      participants: summary.participants || [],
      location: summary.location,
      tags: summary.tags || [],
      summary: summary.summary,
      actionItems: summary.action_items || [],
      decisions: summary.decisions || [],
      deadlines: summary.deadlines || [],
      extractedParticipants: summary.extracted_participants || [],
    };

    const doc = generateWordDocument(summaryData);
    const buffer = await Packer.toBuffer(doc);
    const fileName = `${summary.meeting_title || 'meeting-notes'}-${id}.docx`.replace(
      /[^a-z0-9.-]/gi,
      '-'
    );

    res.setHeader(
      'Content-Type',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    );
    res.setHeader('Content-Disposition', `attachment; filename="${fileName}"`);
    res.setHeader('Content-Length', buffer.length);
    res.send(buffer);
  } catch (error) {
    console.error('Word export error:', error);
    res.status(500).json({
      error: 'Failed to generate Word document',
      details: error.message,
    });
  }
});

export default router;
