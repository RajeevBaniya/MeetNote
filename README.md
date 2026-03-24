# MeetNote

## Project Overview
MeetNote is a meeting application with four connected parts:
- a web client for meeting UI, transcript, chat, and summary screens
- a FastAPI backend for meeting/auth/join/transcript/chat APIs
- a Python agent process for assistant behavior during meetings
- a separate Node backend for summary generation and summary history

Core user flow:
1. User creates or joins a meeting.
2. Meeting runs with video, transcript, chat, and assistant.
3. Transcript content is used to generate a summary.
4. Summary is stored and managed in the Node summarization service.

## System Architecture
Main components:
- `frontend/` (Next.js)
- `backend/api/` (FastAPI + Redis + PostgreSQL)
- `backend/agent/` (Python assistant runtime)
- `summerease/backend/` (Node.js summary service)

High-level request/data path:

```text
Browser (Next.js)
    |
    v
FastAPI API  <----> Redis
    |  \
    |   \----> PostgreSQL
    |
    v
Agent (Python)
    |
    v
Stream events (calls/transcript)
    |
    v
Summarization Backend (Node.js)
```

## Core Features
- Meeting lifecycle:
  - create meeting
  - join with join code and passcode
  - end meeting
- Meeting room:
  - gallery and screen-share layouts
  - overlay panels for participants, chat, transcript
- Transcript:
  - webhook ingestion
  - queue + worker processing
  - stabilization and deduplication before commit
  - live WebSocket streaming to clients
- Chat:
  - Redis-backed message buffer
  - chat WebSocket broadcast to connected users
- Assistant:
  - assistant message path integrated with chat/transcript context
- Summarization:
  - upload and live transcript-based generation paths
  - saved summaries, export, and email

## Data Flow
### Transcript Flow
1. Stream transcript webhook reaches FastAPI transcript webhook handler.
2. Event is queued into Redis (`transcript_events`).
3. Transcript worker consumes queued events.
4. Stabilizer logic applies commit window, dedupe, confidence checks.
5. Final segments are saved to Redis segment keys.
6. Transcript WebSocket pushes finalized segments to meeting clients.

### Chat Flow
1. Frontend sends chat messages through chat WebSocket.
2. FastAPI validates and appends message to Redis meeting chat list.
3. FastAPI broadcasts message to active sockets in that meeting.
4. Frontend reconciles optimistic messages with server messages.

### Assistant Flow
1. Assistant runtime listens to meeting/transcript-related state.
2. Assistant generates response text.
3. Response is posted into chat message flow and rendered in meeting UI.

### Summarization Flow
1. Frontend sends transcript text + instruction to Node summary API.
2. Node summary service generates summary and structured sections.
3. Summary can be persisted and returned with a summary ID.
4. Frontend loads summaries from Node summary history endpoints.

## Tech Stack
- Frontend: Next.js, React
- API backend: FastAPI, SQLAlchemy, asyncpg
- Data/state: Redis, PostgreSQL
- Meeting integration: Stream SDKs
- Summary backend: Node.js, Express

