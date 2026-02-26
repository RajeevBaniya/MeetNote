import { Document } from 'docx'
import { createMeetingNotesTemplate } from './templateBuilder.js'
import { buildDocumentChildren } from './wordContentBuilder.js'

function generateWordDocument(summaryData) {
	const template = createMeetingNotesTemplate(summaryData)
	const children = buildDocumentChildren(template)

	const doc = new Document({
		sections: [
			{
				children,
			},
		],
	})

	return doc
}

export { generateWordDocument }
