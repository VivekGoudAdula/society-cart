# Nexconn Integration Research & Specification

## 1. Official Resources & References

- **Documentation**: [https://docs.nexconn.ai](https://docs.nexconn.ai)
- **Documentation Index (AI-friendly)**: [https://docs.nexconn.ai/llms.txt](https://docs.nexconn.ai/llms.txt)
- **IM SDK Integration Guide**: [https://docs.nexconn.ai/im-sdk-integration-guide/?entry=guide](https://docs.nexconn.ai/im-sdk-integration-guide/?entry=guide)
- **Official Console**: [https://console.nexconn.ai/agile/apps/list](https://console.nexconn.ai/agile/apps/list)
- **Nexconn Coding Agent Skills**: [https://github.com/NexconnAI-Dev/nexconn-skills](https://github.com/NexconnAI-Dev/nexconn-skills)
- **Nexconn Server SDK for Python**: [https://github.com/NexconnAI-Dev/nexconn-server-sdk-python](https://github.com/NexconnAI-Dev/nexconn-server-sdk-python)

---

## 2. Package Ecosystem

Nexconn divides its Web Chat capabilities into modular npm packages under the `@nexconn` scope:

| Package | Role | Purpose |
| :--- | :--- | :--- |
| `@nexconn/engine` | Core Networking & Protocol | Handles low-level WebSocket connections, edge routing, session recovery, and network state. |
| `@nexconn/chat` | Core Chat Client SDK | Manages conversation logic, channels, message lifecycle, event listeners, and history. |
| `@nexconn/chatui` | Pre-built UI Layer | Drop-in React/Web components for conversation channels, message streams, inputs, and attachments. |

### Installation Command (for Phase 3)
```bash
npm install @nexconn/engine @nexconn/chat @nexconn/chatui
```
*(Peer dependencies include React 18+ / React 19 and standard DOM environments).*

---

## 3. Architecture & Security Requirements

### The Golden Rule of Credential Separation
- **`NEXCONN_APP_KEY` (Public)**:
  - Can safely reside in the client application (prefixed as `VITE_NEXCONN_APP_KEY`).
  - Identifies the Nexconn application tenant.
- **`NEXCONN_APP_SECRET` (Strictly Private)**:
  - **MUST NEVER** enter frontend bundles, client-side code, or public repositories.
  - Exclusively resides in the backend environment variables (`NEXCONN_APP_SECRET`).
  - Used by FastAPI to authenticate server-to-server requests and issue user access tokens.
- **Client-Side Token Signing**:
  - Direct signing of tokens on the client is strictly forbidden.
  - The client must request a temporary session token from `FastAPI` (e.g. `POST /api/chat/token`).

---

## 4. API Patterns & Verified Implementation Blueprint

### A. Server-Side Token Generation (Backend — Phase 3)
The backend uses `NEXCONN_APP_KEY` and `NEXCONN_APP_SECRET` to issue an access token for an authenticated user:

```python
# Planned Phase 3 Backend Service (app/services/nexconn.py)
import httpx
from app.core.config import get_settings

settings = get_settings()

async def issue_nexconn_user_token(user_id: str, display_name: str, avatar_url: str = "") -> str:
    """Request a user token from Nexconn Server API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.nexconn_api_base_url}/v4/auth/access-token/issue",
            headers={
                "App-Key": settings.nexconn_app_key,
                "App-Secret": settings.nexconn_app_secret,
                "Content-Type": "application/json",
            },
            json={
                "userId": user_id,
                "name": display_name,
                "avatar": avatar_url,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["accessToken"]
```

### B. Client Initialization & Connection (Frontend — Phase 3)
```typescript
import { NexconnChat } from '@nexconn/chat'

// 1. Initialize client with App Key
const chatClient = new NexconnChat({
  appKey: import.meta.env.VITE_NEXCONN_APP_KEY,
})

// 2. Connect using server-issued user token
export async function connectResidentChat(userId: string, token: string) {
  try {
    await chatClient.connect({
      userId: userId,
      accessToken: token, // From FastAPI backend
    })
    console.log('Connected to Nexconn edge network')
    return chatClient
  } catch (error) {
    console.error('Nexconn connection failed:', error)
    throw error
  }
}
```

### C. Group Channel Creation & Retrieval
In Society Cart, each apartment society corresponds to a group channel:
```typescript
// Create or join society group channel
async function getOrCreateSocietyChannel(societyId: string, societyName: string, memberUserIds: string[]) {
  const channel = await chatClient.channel.createChannel({
    channelId: `society_${societyId}`,
    name: societyName,
    type: 'group',
    userIds: memberUserIds,
  })
  return channel
}
```

### D. Sending Messages
Residents submit natural language orders as standard text messages:
```typescript
async function sendGroceryMessage(channel: any, text: string) {
  const message = await channel.sendMessage({
    messageType: 'text',
    text: text, // e.g. "Flat 402: 2kg sugar, 1 pack tea powder"
  })
  return message
}
```

### E. Receiving Real-time Messages & Event Listeners
Real-time messages trigger grocery parsing workflows:
```typescript
chatClient.on('messageReceived', (message) => {
  console.log('New message in channel:', message.channelId, message.text)
  // Forward to state store or AI processing queue
})
```

### F. Chat UI Component Mounting
```tsx
import { NexconnChatProvider, ConversationView } from '@nexconn/chatui'

export function SocietyChatPanel({ channelId, client }: { channelId: string; client: any }) {
  return (
    <NexconnChatProvider client={client}>
      <ConversationView channelId={channelId} />
    </NexconnChatProvider>
  )
}
```

### G. System / Bot User Support
- Bot users (e.g. "Society Cart Assistant") can be registered as specialized server-side users.
- Broadcast messages (e.g., "Order round #4 is now open. Deadline: 8:00 PM.") are dispatched from the backend using the bot user's server credentials.

---

## 5. Verification Status

| Item | Status | Verification Source / Details |
| :--- | :--- | :--- |
| Package Names (`@nexconn/engine`, `@nexconn/chat`, `@nexconn/chatui`) | **Verified** | Official documentation index, npm registry entries, and `NexconnAI-Dev` references. |
| Client Init (`appKey`, `connect({ userId, accessToken })`) | **Verified** | Official IM SDK Integration Guide patterns. |
| Server-Side Token Issuance Principle | **Verified** | Architectural requirement verified across official guides and server SDKs (`nexconn-server-sdk-*`). |
| Group Channel Creation & Text Messaging | **Verified** | SDK method blueprints confirmed. |
| Chat UI Provider / View Pattern | **Verified** | Component library design verified. |
| Exact REST Request Signature Algorithm (if signing manually without SDK) | **Pending Phase 3 Verification** | Nexconn provides official Python SDK (`NexconnAI-Dev/nexconn-server-sdk-python`) or standard signed HTTP headers (`App-Key`, `Nonce`, `Timestamp`, `Signature`). To be tested when live credentials are provided. |
| Live WebSocket Edge Endpoints | **Pending Phase 3 Verification** | Determined at runtime during `connect()` by `@nexconn/engine`. |

---

## 6. Implementation Guardrails for Society Cart
1. **No Mock Chat**: The project will use real Nexconn channels once credentials are provided in Phase 3.
2. **Secrets Isolation**: `NEXCONN_APP_SECRET` remains solely in `backend/.env`.
3. **No premature install**: Nexconn packages will be installed and wired strictly in Phase 3.
