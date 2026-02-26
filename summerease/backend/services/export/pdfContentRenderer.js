function renderPDFContent(renderer, template) {
	const { addHeading, addSubHeading, addLine } = renderer

	addHeading(template.title)
	addLine('')

	addSubHeading('Meeting Information')
	addLine(`Date & Time: ${template.date}`)
	addLine(`Type: ${template.type}`)
	addLine(`Location: ${template.location}`)

	if (template.participants.length > 0) {
		addLine(`Participants: ${template.participants.join(', ')}`)
	}

	if (template.tags.length > 0) {
		addLine(`Tags: ${template.tags.join(', ')}`)
	}

	addLine('')
	addSubHeading('Summary')
	const summaryLines = template.summary.split('\n').filter((line) => line.trim())
	summaryLines.forEach((line) => {
		addLine(line.trim())
	})

	if (template.actionItems.length > 0) {
		addLine('')
		addSubHeading('Action Items')
		template.actionItems.forEach((item, index) => {
			const taskText = `${index + 1}. ${item.task}`
			addLine(taskText, 0)
			if (item.assignee || item.dueDate) {
				const details = []
				if (item.assignee) details.push(`Assignee: ${item.assignee}`)
				if (item.dueDate) details.push(`Due: ${item.dueDate}`)
				addLine(details.join(' | '), 20)
			}
		})
	}

	if (template.decisions.length > 0) {
		addLine('')
		addSubHeading('Key Decisions')
		template.decisions.forEach((item, index) => {
			addLine(`${index + 1}. ${item.decision}`, 0)
			if (item.context) {
				addLine(`   Context: ${item.context}`, 20)
			}
		})
	}

	if (template.deadlines.length > 0) {
		addLine('')
		addSubHeading('Deadlines')
		template.deadlines.forEach((item, index) => {
			addLine(`${index + 1}. ${item.item}`, 0)
			const details = [`Date: ${item.date}`]
			if (item.owner) details.push(`Owner: ${item.owner}`)
			addLine(details.join(' | '), 20)
		})
	}
}

export { renderPDFContent }
