import { PDFDocument, StandardFonts } from 'pdf-lib'
import { sanitizeText, validateSummaryData } from './exportUtils.js'
import { createMeetingNotesTemplate } from './templateBuilder.js'
import { createPDFRenderer } from './pdfRenderer.js'
import { renderPDFContent } from './pdfContentRenderer.js'

async function generatePDF(summaryData) {
	const validatedData = validateSummaryData(summaryData)
	const template = createMeetingNotesTemplate(validatedData)

	const pdfDoc = await PDFDocument.create()

	const title = sanitizeText(template.title) || 'Untitled Meeting'
	pdfDoc.setTitle(title)
	pdfDoc.setAuthor('SummerEase Meeting Notes')
	pdfDoc.setCreator('SummerEase Meeting Notes Summarizer')
	pdfDoc.setProducer('SummerEase')
	pdfDoc.setCreationDate(new Date())
	pdfDoc.setModificationDate(new Date())

	const timesRomanFont = await pdfDoc.embedFont(StandardFonts.TimesRoman)
	const timesRomanBoldFont = await pdfDoc.embedFont(StandardFonts.TimesRomanBold)

	const page = pdfDoc.addPage([595, 842])
	const dimensions = page.getSize()

	const fonts = { timesRomanFont, timesRomanBoldFont }
	const renderer = createPDFRenderer(pdfDoc, fonts, dimensions)

	renderPDFContent(renderer, template)

	const pdfBytes = await pdfDoc.save()

	if (!pdfBytes || pdfBytes.length === 0) {
		throw new Error('PDF generation failed: empty PDF bytes')
	}

	if (!(pdfBytes instanceof Uint8Array)) {
		throw new Error('PDF generation failed: invalid PDF bytes format')
	}

	if (pdfBytes.length < 100) {
		throw new Error('PDF generation failed: PDF file is too small to be valid')
	}

	const pdfSignature = String.fromCharCode(...pdfBytes.slice(0, 4))
	if (pdfSignature !== '%PDF') {
		throw new Error('PDF generation failed: invalid PDF signature')
	}

	return pdfBytes
}

export { generatePDF }
