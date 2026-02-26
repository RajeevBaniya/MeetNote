import { formatDate, getMeetingTypeLabel } from './exportUtils.js'

function createMeetingNotesTemplate(summaryData) {
	const {
		meetingTitle,
		meetingDate,
		meetingType,
		participants = [],
		location,
		tags = [],
		summary,
		actionItems = [],
		decisions = [],
		deadlines = [],
		extractedParticipants = [],
	} = summaryData

	const allParticipants = [
		...participants,
		...extractedParticipants.filter(
			(p) => !participants.includes(p)
		),
	]

	return {
		title: meetingTitle || 'Untitled Meeting',
		date: formatDate(meetingDate),
		type: getMeetingTypeLabel(meetingType),
		participants: allParticipants,
		location: location || 'Not specified',
		tags,
		summary,
		actionItems,
		decisions,
		deadlines,
	}
}

export { createMeetingNotesTemplate }
