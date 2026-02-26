import {
	Paragraph,
	TextRun,
	HeadingLevel,
	AlignmentType,
	Table,
	TableRow,
	TableCell,
	WidthType,
} from 'docx'

function buildInfoTable(template) {
	
	const infoRows = [
		['Date & Time', template.date],
		['Type', template.type],
		['Location', template.location],
	]

	if (template.participants.length > 0) {
		infoRows.push(['Participants', template.participants.join(', ')])
	}

	if (template.tags.length > 0) {
		infoRows.push(['Tags', template.tags.join(', ')])
	}

	return new Table({
		width: { size: 100, type: WidthType.PERCENTAGE },
		rows: infoRows.map(
			([label, value]) =>
				new TableRow({
					children: [
						new TableCell({
							children: [
								new Paragraph({
									children: [
										new TextRun({
											text: label,
											bold: true,
										}),
									],
								}),
							],
							width: { size: 30, type: WidthType.PERCENTAGE },
						}),
						new TableCell({
							children: [
								new Paragraph({
									children: [
										new TextRun({
											text: value || 'Not specified',
										}),
									],
								}),
							],
							width: { size: 70, type: WidthType.PERCENTAGE },
						}),
					],
				})
		),
	})
}

function buildSummarySection(template) {
	const children = []

	children.push(
		new Paragraph({
			text: 'Summary',
			heading: HeadingLevel.HEADING_1,
			spacing: { before: 400, after: 200 },
		})
	)

	const summaryLines = template.summary
		.split('\n')
		.filter((line) => line.trim())
	summaryLines.forEach((line) => {
		children.push(
			new Paragraph({
				children: [new TextRun({ text: line.trim() })],
				spacing: { after: 100 },
			})
		)
	})

	return children
}

function buildActionItemsSection(template) {
	const children = []

	if (template.actionItems.length === 0) {
		return children
	}

	children.push(
		new Paragraph({
			text: 'Action Items',
			heading: HeadingLevel.HEADING_1,
			spacing: { before: 400, after: 200 },
		})
	)

	template.actionItems.forEach((item, index) => {
		const itemText = `${index + 1}. ${item.task}`
		const runs = [new TextRun({ text: itemText, bold: true })]

		if (item.assignee || item.dueDate) {
			const details = []
			if (item.assignee) details.push(`Assignee: ${item.assignee}`)
			if (item.dueDate) details.push(`Due: ${item.dueDate}`)
			runs.push(new TextRun({ text: ` (${details.join(', ')})` }))
		}

		children.push(
			new Paragraph({
				children: runs,
				spacing: { after: 100 },
			})
		)
	})

	return children
}

function buildDecisionsSection(template) {
	const children = []

	if (template.decisions.length === 0) {
		return children
	}

	children.push(
		new Paragraph({
			text: 'Key Decisions',
			heading: HeadingLevel.HEADING_1,
			spacing: { before: 400, after: 200 },
		})
	)

	template.decisions.forEach((item, index) => {
		const runs = [
			new TextRun({ text: `${index + 1}. ${item.decision}`, bold: true }),
		]

		if (item.context) {
			runs.push(new TextRun({ text: ` - ${item.context}` }))
		}

		children.push(
			new Paragraph({
				children: runs,
				spacing: { after: 100 },
			})
		)
	})

	return children
}

function buildDeadlinesSection(template) {
	const children = []

	if (template.deadlines.length === 0) {
		return children
	}

	children.push(
		new Paragraph({
			text: 'Deadlines',
			heading: HeadingLevel.HEADING_1,
			spacing: { before: 400, after: 200 },
		})
	)

	template.deadlines.forEach((item, index) => {
		const runs = [
			new TextRun({ text: `${index + 1}. ${item.item}`, bold: true }),
		]

		const details = [`Date: ${item.date}`]
		if (item.owner) details.push(`Owner: ${item.owner}`)
		runs.push(new TextRun({ text: ` (${details.join(', ')})` }))

		children.push(
			new Paragraph({
				children: runs,
				spacing: { after: 100 },
			})
		)
	})

	return children
}

function buildDocumentChildren(template) {
	const children = []

	children.push(
		new Paragraph({
			text: template.title,
			heading: HeadingLevel.TITLE,
			alignment: AlignmentType.CENTER,
			spacing: { after: 400 },
		})
	)

	children.push(
		new Paragraph({
			text: 'Meeting Information',
			heading: HeadingLevel.HEADING_1,
			spacing: { before: 200, after: 200 },
		})
	)

	children.push(buildInfoTable(template))
	children.push(...buildSummarySection(template))
	children.push(...buildActionItemsSection(template))
	children.push(...buildDecisionsSection(template))
	children.push(...buildDeadlinesSection(template))

	return children
}

export { buildDocumentChildren }
