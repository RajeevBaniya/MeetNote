function formatDate(dateString) {
	if (!dateString) return 'Not specified'
	try {
		const date = new Date(dateString)
		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		})
	} catch {
		return dateString
	}
}

function formatDateOnly(dateString) {
	if (!dateString) return 'Not specified'
	try {
		const date = new Date(dateString)
		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
		})
	} catch {
		return dateString
	}
}

function getMeetingTypeLabel(type) {
	const labels = {
		team: 'Team Meeting',
		'one-on-one': '1-on-1',
		client: 'Client Meeting',
		standup: 'Standup',
		'project-review': 'Project Review',
		brainstorm: 'Brainstorming',
		interview: 'Interview',
		training: 'Training',
		other: 'Other',
	}
	return labels[type] || type || 'Not specified'
}

function sanitizeText(text) {
	if (!text || typeof text !== 'string') {
		return ''
	}
	return text
		.replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, '')
		.replace(/\uFFFD/g, '')
		.trim()
}

function wrapText(text, maxWidth, font, fontSize) {
	if (!text || typeof text !== 'string') {
		return ['']
	}
	
	const sanitized = sanitizeText(text)
	if (!sanitized) {
		return ['']
	}

	const words = sanitized.split(/\s+/).filter(word => word.length > 0)
	if (words.length === 0) {
		return ['']
	}

	const lines = []
	let currentLine = ''

	for (const word of words) {
		const testLine = currentLine ? `${currentLine} ${word}` : word
		const width = font.widthOfTextAtSize(testLine, fontSize)
		
		if (width > maxWidth && currentLine) {
			lines.push(currentLine)
			currentLine = word
		} else {
			currentLine = testLine
		}
	}
	
	if (currentLine) {
		lines.push(currentLine)
	}
	
	return lines.length > 0 ? lines : [sanitized]
}

function validateSummaryData(summaryData) {
	if (!summaryData || typeof summaryData !== 'object') {
		throw new Error('Invalid summary data: data is required')
	}

	if (!summaryData.summary || typeof summaryData.summary !== 'string' || summaryData.summary.trim().length === 0) {
		throw new Error('Invalid summary data: summary text is required')
	}

	return {
		meetingTitle: summaryData.meetingTitle || 'Untitled Meeting',
		meetingDate: summaryData.meetingDate || null,
		meetingType: summaryData.meetingType || null,
		participants: Array.isArray(summaryData.participants) ? summaryData.participants : [],
		location: summaryData.location || null,
		tags: Array.isArray(summaryData.tags) ? summaryData.tags : [],
		summary: String(summaryData.summary).trim(),
		actionItems: Array.isArray(summaryData.actionItems) ? summaryData.actionItems : [],
		decisions: Array.isArray(summaryData.decisions) ? summaryData.decisions : [],
		deadlines: Array.isArray(summaryData.deadlines) ? summaryData.deadlines : [],
		extractedParticipants: Array.isArray(summaryData.extractedParticipants) ? summaryData.extractedParticipants : [],
	}
}

export { formatDate, formatDateOnly, getMeetingTypeLabel, sanitizeText, wrapText, validateSummaryData }
