# Project Progress — Society Cart

**Project**: Society Cart  
**Tagline**: Your Society. One Chat. One Bulk Order.  
**Hackathon**: Nexconn Build Challenge 2026 (Track: Social & Community)  
**Current Phase**: Phase 0 — Workspace Preparation & Architecture  
**Completed Phases**: None (Phase 0 completed, awaiting user approval to transition)  
**Next Phase**: Phase 1 — UI Foundation & Application Layout  

---

## Phases Checklist

- [x] **Phase 0 — Workspace Preparation & Architecture**
  - [x] Environment inspection (Node.js, npm, Python, Git, Ports 5173 & 8000).
  - [x] Project structure initialization (`frontend/`, `backend/`, `docs/`).
  - [x] Frontend foundation: React 19 + Vite + TypeScript + Tailwind CSS v4 + Lucide React.
  - [x] Backend foundation: FastAPI + Python 3.13 venv + Uvicorn + Pydantic Settings.
  - [x] Root `.gitignore` and `.env.example` security templates.
  - [x] MongoDB Atlas setup documentation.
  - [x] Nexconn Chat SDK & Server API research and specifications (`docs/NEXCONN_INTEGRATION.md`).
  - [x] System architecture blueprint (`docs/ARCHITECTURE.md`).
  - [x] End-to-end verification (Vite dev server, Vite production build, FastAPI live server, CORS preflight).

- [ ] **Phase 1 — UI Foundation & Application Layout**
  - [ ] Visual design system and responsive navigation.
  - [ ] Screen 1: Welcome / Login.
  - [ ] Screen 2: Create or Join a Society.
  - [ ] Screen 3: Resident Dashboard.
  - [ ] Screen 4: Volunteer Dashboard.
  - [ ] Screen 5: Society Chat Screen.
  - [ ] Screen 6: Shopping List Screen.
  - [ ] Screen 7: Order & Savings Summary.

- [ ] **Phase 2 — Backend, Database & User Management**
  - [ ] MongoDB Atlas connection and PyMongo configuration.
  - [ ] User authentication, session management, and flat profiles.
  - [ ] Role-based access control (Admin, Resident, Volunteer).
  - [ ] Society creation and membership join codes.
  - [ ] Core collections: `users`, `societies`, `memberships`.

- [ ] **Phase 3 — Real Nexconn Chat Integration**
  - [ ] Secure backend token generation service (`POST /v4/auth/access-token/issue`).
  - [ ] Client SDK initialization (`@nexconn/chat`, `@nexconn/engine`).
  - [ ] Real group channel creation and retrieval for societies.
  - [ ] Real-time message exchange and event listeners.
  - [ ] Message history synchronization.
  - [ ] System / Bot user identity.

- [ ] **Phase 4 — Grocery Order Rounds**
  - [ ] Volunteer opening and closing order rounds with deadlines.
  - [ ] Active round banner and real-time state in chat.
  - [ ] Linking chat messages to the active round.
  - [ ] Post-closure correction workflow.

- [ ] **Phase 5 — AI Grocery Understanding**
  - [ ] Groq API integration (Llama 3 inference).
  - [ ] Multilingual parsing (English, Hindi, Telugu natural language).
  - [ ] Structured extraction: Flat, Item, Quantity, Unit, Category.
  - [ ] Unclear quantity handling and clarification prompts.
  - [ ] AI confirmation bot messages in Nexconn group chat.

- [ ] **Phase 6 — Volunteer Shopping Dashboard**
  - [ ] Master shopping list compilation across all flats.
  - [ ] Category-wise aggregation (Rice & Grains, Oil, Dairy, etc.).
  - [ ] Total quantity calculation.
  - [ ] Packing breakdown by individual flat.
  - [ ] Exportable/printable shopping checklist.

- [ ] **Phase 7 — Billing & Savings**
  - [ ] Volunteer actual purchase price recording.
  - [ ] Per-flat itemized billing and allocation.
  - [ ] Bill publication in Nexconn chat.
  - [ ] Savings calculation against verified benchmark retail prices.

- [ ] **Phase 8 — Testing, Security & UX Polish**
  - [ ] Multi-resident concurrency and duplicate message handling.
  - [ ] Role permission and billing privacy isolation tests.
  - [ ] Nexconn reconnect and edge failover handling.
  - [ ] Responsive testing across desktop and mobile.

- [ ] **Phase 9 — Deployment & Hackathon Submission**
  - [ ] Frontend deployment (Vercel).
  - [ ] Backend deployment (Render / Cloud Python host).
  - [ ] Production MongoDB Atlas and Nexconn credentials.
  - [ ] End-to-end live testing.
  - [ ] Demo video, documentation PDF, and repository publication.
