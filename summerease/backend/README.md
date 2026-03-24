# Summerease Backend

## Overview
`summerease/backend` is a separate Express service dedicated to meeting summary features.  
It is not part of FastAPI runtime logic and has its own API routes for summary workflows.

Server entry: `summerease/backend/server.js`.

## Responsibilities
- generate summary text from transcript + instruction
- persist and query summary records
- edit and delete saved summaries
- export summaries as PDF and Word
- send summary content by email

## API Surface
Routes currently wired in `server.js`:
- `POST /api/summary/generate`
- `GET /api/summaries`
- `GET /api/summaries/:id`
- `PUT /api/summaries/:id`
- `DELETE /api/summaries/:id`
- `GET /api/export/pdf/:id`
- `GET /api/export/word/:id`
- `POST /api/email/send`
- `POST /api/upload/*` (text extraction/upload helper path)

## Summary Generation Flow
1. Frontend sends transcript and instruction to `POST /api/summary/generate`.
2. Route calls generation service (`services/groq.js`).
3. Service returns summary and structured fields.
4. If persistence is enabled, summary is saved through `services/summaries.js`.
5. Response includes generated content and optional saved summary id.

## Live vs Upload
- Live path: frontend sends transcript content captured from live meeting flow.
- Upload path: frontend uploads file content, extracts transcript text, then generates summary.

## Data Ownership
- Summary records are stored and managed in this Node service.
- FastAPI is not used as summary persistence for this flow.
- Summary list/detail/update/delete and export/email all use this service’s APIs.
