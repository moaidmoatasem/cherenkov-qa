## Summary
Adds a React ChatScreen component that connects to the Phase 4 SSE streaming chat API and integrates it into the dashboard UI.

## Changes
- ChatScreen.tsx — Full chat component with session management, message bubbles, SSE streaming, input field
- routes.tsx — Chat route definition
- App.tsx — Chat tab rendering
- Sidebar.tsx — Chat nav item under LEARN section
- api.ts — createChatSession() and fetchChatMessages() API functions
- api_mocks.ts — Mocks for chat endpoints
- dashboard_e2e.spec.ts — E2E test for chat screen (session creation, message send, SSE response)

## Build
- Vite build: passed (1726 modules, 3.33s)
- TypeScript: clean (no new errors)

## API Endpoints Used
- POST /api/v1/chat/sessions — create session
- POST /api/v1/chat/sessions/{id}/stream — SSE streaming response
- GET /api/v1/chat/sessions/{id}/messages — message history
