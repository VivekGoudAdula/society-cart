# Project Progress — Society Cart

**Project**: Society Cart  
**Tagline**: Your Society. One Chat. One Bulk Order.  
**Hackathon**: Nexconn Build Challenge 2026 (Track: Social & Community)  
**Current Phase**: Phase 4 — Grocery Order Rounds (Completed & 100% Verified)  
**Completed Phases**: Phase 0, Phase 1, Phase 2, Phase 3, Phase 4  
**Next Phase**: Phase 5 — AI Grocery Understanding  

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

- [x] **Phase 1 — UI Foundation & Application Layout**
  - [x] Visual design system (Tailwind v4 tokens: `#23865B` primary, `#EAF5EE` surface, `#18231E` text).
  - [x] Reusable component library (`Button`, `Input`, `SearchInput`, `Card`, `Badge`, `Avatar`, `Modal`, `ConfirmationDialog`, `StatCard`, `PageHeader`, `EmptyState`, `LoadingPlaceholder`).
  - [x] Screen 1: Welcome / Login with role demo portals and 3-step value workflow (`/`).
  - [x] Screen 2: Create or Join a Society with tab selection cards and simulated confirmation (`/society-setup`).
  - [x] Screen 3: Resident Dashboard with active round card, quick metrics, activity feed, and quick actions (`/resident`).
  - [x] Screen 4: Volunteer Operations Dashboard with active round logistics controller, close-round modal, and completed drives archive (`/volunteer`).
  - [x] Screen 5: Society Chat Screen with multi-lingual demo messages (English, Telugu, Hindi), AI structured interpretation cards, instant send interaction, and prototype disclaimer banner (`/chat`).
  - [x] Screen 6: Consolidated Shopping List Screen with master item procurement checklists, category filters, search, flat packing manifest, and print-friendly export (`/shopping-list`).
  - [x] Screen 7: Order & Savings Summary with itemized receipt, benchmark comparison formula ($Savings = Retail - Bulk$), and past round archives (`/order-summary`).
  - [x] Desktop sticky sidebar and mobile bottom thumb navigation bar.
  - [x] Dynamic role-switching between Resident (Rahul, C-402) and Volunteer (Priya, B-204).
  - [x] Central realistic Indian apartment mock data (`Greenfield Heights Residency`, Kondapur, Hyderabad).
  - [x] Production build verification (`tsc -b && vite build`) passed with 0 errors.

- [x] **Phase 2 — Backend, Database & User Management**
  - [x] MongoDB Atlas connection and PyMongo asynchronous client lifecycle management.
  - [x] Core collections with strict uniqueness indexes:
    - `users.email` (unique)
    - `societies.invite_code` (unique)
    - `memberships.(user_id, society_id)` (unique for active memberships)
    - `memberships.(society_id, flat_number)` (unique for active memberships in a society)
  - [x] Secure authentication with bcrypt password hashing and JWT access & refresh tokens.
  - [x] User management APIs: register, login, refresh, logout, `/auth/me`, and `/users/me` (protecting sensitive fields).
  - [x] Society management APIs:
    - Create society with automatic unique 8-character invite code and automatic `admin` membership for creator.
    - Join society using invite code and flat number (with duplicate check and occupied flat check).
    - Society member listing and admin volunteer promotion/revocation (`PATCH /api/societies/{id}/members/{id}/role`).
    - Cross-society data isolation.
  - [x] Role-Based Access Control (RBAC): `admin`, `volunteer`, `resident` with dependency guards.
  - [x] Automated test suite covering all 15 scenarios in `backend/tests/test_phase2.py` (14/14 tests passed).
  - [x] Connected frontend to real APIs:
    - `frontend/src/services/api.ts` complete API client and token storage.
    - `AppContext.tsx` authenticated session restoration, real login/register/logout/createSociety/joinSociety.
    - `WelcomePage.tsx` tabbed Sign In & Register forms with real backend error feedback.
    - `SocietySetupPage.tsx` real society creation and code copy, real join with error handling.
    - `VolunteerDashboard.tsx` real society roster view and Admin volunteer promotion/demotion.
    - `Header.tsx` & `Sidebar.tsx` real user profile, flat number, role badges, and multiple-society switcher.
  - [x] Full production frontend build (`tsc -b && vite build`) passed with 0 errors.

- [x] **Phase 3 — Real Nexconn Chat Integration**
  - [x] Server API authentication headers using SHA1 algorithm (`App-Key`, `Nonce`, `Timestamp`, `Signature`).
  - [x] Live regional Nexconn cluster connection (`https://api-sg01.ronghub.com` - AreaCode.SG).
  - [x] Secure backend chat token generation endpoint (`POST /api/chat/token`) verifying active society membership.
  - [x] Cross-society chat isolation returning HTTP 403 Forbidden for non-members.
  - [x] Nexconn Group Channel auto-provisioning upon society creation (`nexconn_group_id: society_{id}`).
  - [x] Dynamic member synchronization (`add_resident_to_group`, `remove_resident_from_group`) on society join/leave.
  - [x] System / Bot user identity and broadcasting endpoint (`POST /api/chat/system-message`).
  - [x] Installed official client packages: `@nexconn/engine@26.5.1` and `@nexconn/chat@26.5.1`.
  - [x] Singleton `NexconnClient` service with connection state listeners, message stream, and history pagination.
  - [x] Frontend `ChatContext` providing real-time message stream, connection status (`Nexconn Live`), member lookup map for flat/name attribution, and send handlers.
  - [x] Updated `SocietyChatPage.tsx` with live status indicator, real-time message feed, sending states, and error handling while preserving Phase 1 visual styling.
  - [x] Backend test suite `backend/tests/test_phase3.py` (6/6 test groups passed).
  - [x] End-to-end two-user verification script (`verify_e2e_chat.py`): verified Resident A (Flat A-101) & Resident B (Flat B-204) real message exchange and cross-society 403 isolation with 100% compliance.
  - [x] Frontend production build (`tsc -b && vite build`) verified with 0 errors.

- [x] **Phase 4 — Grocery Order Rounds**
  - [x] `order_rounds` collection with partial unique index ensuring at most one active round per society.
  - [x] `grocery_submissions` collection linking real Nexconn message IDs with resident flats and rounds.
  - [x] Volunteer/admin APIs: create round (draft), open round (open), close round (closed), list rounds, get active round.
  - [x] Role-Based Access Control enforcing volunteer/admin privilege on round lifecycle actions.
  - [x] Real Nexconn system announcements broadcasted when rounds open and close via `POST /message/group/publish.json`.
  - [x] Automatic deadline enforcement: background scheduler task running every 10s plus on-demand lazy expiration check.
  - [x] Grocery order submission endpoint (`POST /api/societies/{id}/rounds/{id}/submissions`) rejecting submissions after round closure.
  - [x] Frontend `AppContext` & `ChatContext` real-time state synchronization upon receiving round announcements.
  - [x] Resident Dashboard & Society Chat dynamic active round banner with live countdown timer and order submission toggle.
  - [x] Volunteer Operations Dashboard with Start Round modal, Close Round modal, and historical rounds table.
  - [x] Backend test suite `backend/tests/test_phase4.py` (7 test groups, 16 scenarios, 100% passed).
  - [x] End-to-end multi-user script verifying Volunteer Priya, Resident Rahul, Resident Sneha message exchange, closure, and auto-expiration.
  - [x] Frontend production build (`tsc -b && vite build`) passed with 0 errors.

- [x] **Phase 5 — AI Grocery Understanding**
  - [x] Groq API integration with high-performance model (`openai/gpt-oss-120b`) and structured JSON schema enforcement.
  - [x] Multilingual natural-language understanding across English, Hindi, Telugu, and mixed code-switching.
  - [x] Canonical Indian grocery normalization across 10 categories (`grains_rice`, `pulses`, `vegetables`, `fruits`, `dairy`, `cooking_oils`, `spices`, `household_essentials`, `personal_care`, `other`).
  - [x] Intelligent brand, item, quantity, and unit extraction with colloquial verb filtering (e.g. "teesko", "lelo").
  - [x] Missing quantity and ambiguity detection with interactive resident clarification prompts.
  - [x] Resident Review & Confirmation workflow with item-level manual quantity/brand/unit editing.
  - [x] Strict privacy and authorization isolation: individual orders, items, and clarifications remain private to the resident dashboard and order review UI (never broadcasted to public society chat).
  - [x] Atomic background extraction recovery with exclusive lease claiming (`processing_lease_id`, `processing_lease_until`) preventing race conditions and stale overwrites.
  - [x] Full backend test suite `backend/tests/test_phase5.py` (10/10 passed) and live Groq multilingual suite (4/4 passed).
  - [x] Frontend `OrderReviewCard` and `ClarificationModal` components fully integrated with production build passing.

- [x] **Phase 6 — Volunteer Shopping Dashboard**
  - [x] Master shopping list compilation across all confirmed resident orders via `POST /api/societies/{id}/rounds/{id}/shopping-list/compile`.
  - [x] Strict order eligibility: only `confirmed` orders are aggregated; `pending_review`, `needs_clarification`, `processing`, `failed`, and `rejected` are excluded.
  - [x] Unconfirmed order warnings with explicit count and inspection list for unresolved orders.
  - [x] Canonical category-wise aggregation across the 10 canonical categories with safe compatible unit normalizations (g -> kg, ml -> L).
  - [x] Deterministic item combination rules: brand, variant, category, and unit differences remain cleanly separated.
  - [x] Individual Flat-wise Packing Breakdown: grouped by flat with resident identity, item details, brands, and interactive packing checkboxes.
  - [x] Compilation versioning and idempotency: atomic upsert recalculates fresh from source orders without double-counting.
  - [x] Role-Based Access Control: volunteer and admin privilege enforced; resident and cross-society access blocked with 403 Forbidden.
  - [x] Print-friendly checklist layout (`@media print` CSS, white background, A4 paper optimized, checkboxes).
  - [x] RFC 4180 compliant CSV export for both consolidated bulk manifest and flat-wise packing list.
  - [x] Automated test suite `backend/tests/test_phase6.py` (6/6 passed) and full regression suite (47/47 passed).
  - [x] Frontend `ShoppingListPage.tsx` and `VolunteerDashboard.tsx` integrated with clean production build (`tsc -b && vite build`).

- [x] **Phase 7 — Billing & Savings**
  - [x] Actual purchase cost recording with shop name, receipt/invoice reference, store notes, and explicit substitution tracking.
  - [x] Decimal-safe monetary arithmetic with paise precision (`Decimal('0.01')` using `ROUND_HALF_UP`) ensuring exact mathematical reconciliation: `Total Purchase = Total Allocated + Total Shared + Total Unallocated`.
  - [x] Per-flat physical allocation matching volunteer packing breakdown; support for explicit physical distribution overrides (`flat_allocations_override`) preventing residents from ever being billed for unfulfilled quantities.
  - [x] Clear distinction between unfulfilled resident demand and unallocated inventory surplus.
  - [x] Shared expense distribution (e.g., auto / transport / delivery fee) with deterministic single-paise residual allocation.
  - [x] Immutable bill documents with versioning and atomic compare-and-swap (CAS) to prevent concurrent conflicting version branches.
  - [x] Privacy-safe Nexconn group chat announcements with atomic `"sending"` pre-locks preventing duplicate dispatch; zero private flat numbers or individual amounts revealed.
  - [x] Strict resident privacy isolation: residents can only retrieve their own flat's itemized bill (`GET /api/users/me/bills`); cross-flat and cross-society access blocked with 403 Forbidden.
  - [x] Evidence-backed retail benchmark library with mandatory `pending` verification state, explicit volunteer/admin verification endpoint (`PATCH .../benchmarks/{id}/verify`), and stale evidence filtering (>90 days).
  - [x] Transparent bulk savings engine with strict product/brand/variant/unit comparability, actual allocated quantity weighting, zero extrapolation of partial coverage, and honest zero/negative reporting.
  - [x] Complete backend test suite `backend/tests/test_phase7.py` (17/17 passed) and comprehensive full regression suite across all phases (66/66 passed).
  - [x] Frontend `PurchaseRecordingSection`, `CostAllocationSection`, `SpendingAndSavingsSection`, and Resident `OrderSummaryPage` integrated with production build passing (`tsc -b && vite build` in 10.07s).

- [x] **Phase 8 — Testing, Security & UX Polish**
  - [x] Multi-resident concurrency and duplicate message handling: 6/6 tests passed verifying simultaneous submissions, round closure races, cross-society reservation isolation, duplicate Nexconn message idempotency (409 Conflict), repeated reservation retries, and simultaneous confirmation vs rejection conflict resolution.
  - [x] AI parsing and multilingual grocery quantity edge cases: 5/5 tests passed verifying Telugu colloquial verb filtering ("teesko", "tesko"), Hindi brand and taxonomy preservation ("Aashirvaad", "Tata", "Vijaya"), missing/ambiguous quantity clarification triggers, resident item editing before confirmation, and terminal state immutability against stale AI worker commits.
  - [x] Security, RBAC permissions, and billing privacy: 5/5 tests passed verifying cross-society isolation, flat-level billing privacy, role enforcement (volunteer/admin vs resident), authentication edge cases, and automated audit confirming zero credential exposure in error traces or responses.
  - [x] Order deadline enforcement and financial reconciliation: 5/5 tests passed verifying exact deadline rules (closed rounds reject new submissions while reserving on-time allows confirmation), paise-level mathematical reconciliation identity (`Actual Purchases = Allocated Cost + Unallocated Inventory`), brand/variant separation in purchases, physical allocation overrides (Case A equal vs Case B skewed), and retail benchmark lifecycle with honest negative savings calculation.
  - [x] Full End-to-End Workflow Verification: 1/1 test covering all 15 stages without manual DB manipulation (Admin registration -> Society creation -> Multi-resident onboarding -> Round creation -> Reservation -> AI extraction -> Resident review/editing/confirmation -> Round closure -> Shopping list compilation -> Purchase recording -> Allocation & bill finalization -> Resident billing verification -> Benchmark verification -> Savings calculation -> Privacy-safe Nexconn chat announcement).
  - [x] Nexconn reconnect and edge failover handling: Exponential backoff reconnect loop in `nexconnClient.ts`, message deduplication and unmount safety in `ChatContext.tsx`, and interactive retry controls in `SocietyChatPage.tsx`.
  - [x] Backend startup and scheduler stability: Safe background recovery in `main.py` lifespan and `order_service.py` to prevent unretrieved task exceptions on initial MongoDB connection drops; 15-second backoff in `round_scheduler.py` to eliminate error log spam.
  - [x] Full regression test suite: 88/88 tests passed across Phases 2 through 8 with zero failures.
  - [x] Frontend production build (`tsc -b && vite build`) passed with 0 errors across 2,180 modules.

- [ ] **Phase 9 — Deployment & Hackathon Submission**
  - [ ] Frontend deployment (Vercel).
  - [ ] Backend deployment (Render / Cloud Python host).
  - [ ] Production MongoDB Atlas and Nexconn credentials.
  - [ ] End-to-end live testing.
  - [ ] Demo video, documentation PDF, and repository publication.
