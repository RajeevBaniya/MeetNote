import { rgb } from 'pdf-lib'
import { sanitizeText, wrapText } from './exportUtils.js'

function createPDFRenderer(pdfDoc, fonts, dimensions) {
	const { width, height } = dimensions
	const margin = 50
	const maxTextWidth = width - (margin * 2)
	const fontSize = 11
	const headingSize = 16
	const subHeadingSize = 13
	let currentPage = pdfDoc.getPages()[0]
	let yPosition = height - margin

	const { timesRomanFont, timesRomanBoldFont } = fonts

	function addText(text, options = {}) {
		const {
			x = margin,
			y = yPosition,
			size = fontSize,
			font = timesRomanFont,
			color = rgb(0, 0, 0),
			bold = false,
			wrap = false,
		} = options

		const sanitized = sanitizeText(text)
		if (!sanitized) return 0

		const fontToUse = bold ? timesRomanBoldFont : font
		
		if (wrap) {
			const lines = wrapText(sanitized, maxTextWidth, fontToUse, size)
			lines.forEach((line, index) => {
				if (yPosition < margin + 50) {
					currentPage = pdfDoc.addPage([595, 842])
					yPosition = height - margin
				}
				currentPage.drawText(line, {
					x,
					y: yPosition - (index * (size + 3)),
					size,
					font: fontToUse,
					color,
				})
			})
			return lines.length * (size + 3)
		} else {
			currentPage.drawText(sanitized, {
				x,
				y,
				size,
				font: fontToUse,
				color,
			})
			return size + 5
		}
	}

	function addHeading(text, size = headingSize) {
		const sanitized = sanitizeText(text)
		if (!sanitized) return 0
		
		const lineHeight = addText(sanitized, {
			size,
			font: timesRomanBoldFont,
			color: rgb(0.2, 0.5, 0.3),
		})
		yPosition -= lineHeight + 10
		return lineHeight
	}

	function addSubHeading(text) {
		const sanitized = sanitizeText(text)
		if (!sanitized) return 0
		
		const lineHeight = addText(sanitized, {
			size: subHeadingSize,
			font: timesRomanBoldFont,
			color: rgb(0.3, 0.3, 0.3),
		})
		yPosition -= lineHeight + 8
		return lineHeight
	}

	function addLine(text, indent = 0) {
		if (yPosition < margin + 50) {
			currentPage = pdfDoc.addPage([595, 842])
			yPosition = height - margin
		}

		const sanitized = sanitizeText(text)
		if (!sanitized) return 0

		const lineHeight = addText(sanitized, {
			x: margin + indent,
			y: yPosition,
			wrap: true,
		})
		yPosition -= lineHeight
		return lineHeight
	}

	return { addHeading, addSubHeading, addLine }
}

export { createPDFRenderer }
