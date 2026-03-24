# Frontend

## Overview
The frontend is a Next.js app router project in `frontend/app`. It covers:
- meeting creation/join and meeting room experience
- live transcript and chat overlays
- meeting list/history screens
- summarize flow for upload and live meeting transcript

Main route areas:
- `app/meeting/`
- `app/meetings/`
- `app/summarize/`

## Folder Structure
- `app/components/`
  - reusable UI and feature components
  - `meeting-room/` split by domains (`chat/`, `layout/`, `modals/`, `participants/`, `transcript/`, `toolbar/`, `shell/`)
- `app/lib/`
  - feature logic and state hooks
  - meeting, transcript, chat, summarize, and API helper logic
- `app/providers/`
  - app-level providers (auth, stream context)
- `app/features/`
  - feature-oriented page sections

## Key Systems
### Meeting Room
- `meeting-room.jsx` composes call state, transcript state, and overlays.
- Layout rendering is split into dedicated layout modules.
- Overlays are isolated into their own modules (chat, transcript, participants, modals).

### Transcript
- `use-live-transcript.js` handles transcript WebSocket lifecycle.
- Maintains ordered transcript state using sequence merge logic.
- Supports reconnect/backoff and connection state reporting.
- Feeds summarize handoff through snapshot-based flow.

### Chat
- `use-meeting-chat.js` handles chat WebSocket lifecycle and send flow.
- Uses optimistic messages and reconciliation from server events.
- Tracks unread count when chat panel is closed.
- Handles reconnect and connection state transitions.

### Summarization UI
- Summarize flow is under `app/summarize/`.
- Live mode consumes transcript/snapshot context from meeting flow.
- Generate flow writes saved summaries and refreshes summary list.
- Current UX is generate-and-save (no separate preview-only save step).

## State Management
- State is hook-driven and feature-local.
- Each domain has a primary hook as source of truth:
  - chat: `use-meeting-chat`
  - transcript: `use-live-transcript`
  - summarize flow: `use-live-summary` + summarize helpers
- Components mostly receive prepared state/handlers through props.

