import axios from 'axios'
import dotenv from 'dotenv'

dotenv.config()

const GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
const API_KEY = process.env.GROQ_API_KEY
const MODEL_NAME = process.env.GROQ_MODEL

function validateConfig() {
	if (!API_KEY) {
		throw new Error('Groq API key not configured')
	}
	if (!MODEL_NAME) {
		throw new Error('Groq model not configured')
	}
}

async function callGroqApi(messages, maxTokens = 1000) {
	const response = await axios.post(GROQ_API_URL, {
		model: MODEL_NAME,
		messages,
		temperature: 0.7,
		max_tokens: maxTokens
	}, {
		headers: {
			'Authorization': `Bearer ${API_KEY}`,
			'Content-Type': 'application/json'
		}
	})
	return response.data.choices[0].message.content
}

export async function generateSummary(transcript, instruction) {
	validateConfig()

	const prompt = `
${instruction}

Here is the meeting transcript to summarize:

${transcript}

Please provide a well-structured summary based on the instruction above.
	`.trim()

	try {
		return await callGroqApi([{ role: 'user', content: prompt }])
	} catch (error) {
		console.error('Groq API error:', error.response?.data || error.message)
		throw new Error('Failed to generate summary')
	}
}

export async function extractStructuredData(transcript) {
	validateConfig()

	const prompt = `
Analyze the following meeting transcript and extract structured information.
Return ONLY a valid JSON object with no additional text or explanation.

The JSON must have this exact structure:
{
  "actionItems": [
    { "task": "string", "assignee": "string or null", "dueDate": "string or null" }
  ],
  "decisions": [
    { "decision": "string", "context": "string or null" }
  ],
  "deadlines": [
    { "item": "string", "date": "string", "owner": "string or null" }
  ],
  "participants": ["string"]
}

If no items found for a category, return an empty array.
Extract participant names from the transcript based on who spoke or was mentioned.

Meeting transcript:
${transcript}
	`.trim()

	try {
		const response = await callGroqApi([{ role: 'user', content: prompt }], 1500)
		return parseStructuredResponse(response)
	} catch (error) {
		console.error('Structured extraction error:', error.response?.data || error.message)
		return getEmptyStructuredData()
	}
}

function parseStructuredResponse(response) {
	try {
		const jsonMatch = response.match(/\{[\s\S]*\}/)
		if (!jsonMatch) {
			return getEmptyStructuredData()
		}
		const parsed = JSON.parse(jsonMatch[0])
		return {
			actionItems: Array.isArray(parsed.actionItems) ? parsed.actionItems : [],
			decisions: Array.isArray(parsed.decisions) ? parsed.decisions : [],
			deadlines: Array.isArray(parsed.deadlines) ? parsed.deadlines : [],
			participants: Array.isArray(parsed.participants) ? parsed.participants : []
		}
	} catch {
		return getEmptyStructuredData()
	}
}

function getEmptyStructuredData() {
	return {
		actionItems: [],
		decisions: [],
		deadlines: [],
		participants: []
	}
}

export async function generateMeetingSummary(transcript, instruction, extractStructured = true) {
	validateConfig()

	const summaryPromise = generateSummary(transcript, instruction)

	if (!extractStructured) {
		const summary = await summaryPromise
		return { summary, structured: getEmptyStructuredData() }
	}

	const [summary, structured] = await Promise.all([
		summaryPromise,
		extractStructuredData(transcript)
	])

	return { summary, structured }
}
