import path from 'path'
import { createRequire } from 'module'
import mammoth from 'mammoth'

const require = createRequire(import.meta.url)
const pdfParse = require('pdf-parse')

const SUPPORTED_MIME_TYPES = Object.freeze({
	'text/plain': 'txt',
	'application/pdf': 'pdf',
	'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx'
})

const SUPPORTED_EXTENSIONS = Object.freeze(['.txt', '.pdf', '.docx'])

const MAX_FILE_SIZE = 10 * 1024 * 1024

function getFileExtension(filename) {
	return path.extname(filename).toLowerCase()
}

function isValidMimeType(mimeType) {
	return Object.hasOwn(SUPPORTED_MIME_TYPES, mimeType)
}

function isValidExtension(filename) {
	const ext = getFileExtension(filename)
	return SUPPORTED_EXTENSIONS.includes(ext)
}

function validateFile(file) {
	if (!file) {
		return { valid: false, error: 'No file provided' }
	}

	if (!isValidMimeType(file.mimetype) && !isValidExtension(file.originalname)) {
		return {
			valid: false,
			error: `Unsupported file type. Allowed: ${SUPPORTED_EXTENSIONS.join(', ')}`
		}
	}

	if (file.size > MAX_FILE_SIZE) {
		return {
			valid: false,
			error: `File too large. Maximum size: ${MAX_FILE_SIZE / (1024 * 1024)}MB`
		}
	}

	return { valid: true, error: null }
}

function extractTextFromTxt(buffer) {
	const content = buffer.toString('utf8')
		return content.trim()
}

async function extractTextFromPdf(buffer) {
	const options = { verbosityLevel: 0 }
	const data = await pdfParse(buffer, options)
		return data.text.trim()
}

async function extractTextFromDocx(buffer) {
	const result = await mammoth.extractRawText({ buffer })
		return result.value.trim()
}

function getExtractorForFile(filename, mimeType) {
	const ext = getFileExtension(filename)

	if (ext === '.pdf' || mimeType === 'application/pdf') {
		return extractTextFromPdf
	}

	if (ext === '.docx' || mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
		return extractTextFromDocx
	}

	if (ext === '.txt' || mimeType === 'text/plain') {
		return extractTextFromTxt
	}

	return null
}

async function extractText(file) {
	const validation = validateFile(file)

	if (!validation.valid) {
		throw new Error(validation.error)
	}

	if (!file.buffer) {
		throw new Error('File buffer is missing')
	}

	const extractor = getExtractorForFile(file.originalname, file.mimetype)

	if (!extractor) {
		throw new Error('No extractor available for this file type')
	}

	const text = await extractor(file.buffer)

	if (!text || text.length === 0) {
		throw new Error('Could not extract text from file. The file may be empty or corrupted.')
	}

	return text
}

export {
	extractText,
	validateFile,
	SUPPORTED_EXTENSIONS,
	SUPPORTED_MIME_TYPES,
	MAX_FILE_SIZE
}
