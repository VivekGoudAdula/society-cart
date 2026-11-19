# Society Cart

> **Your Society. One Chat. One Bulk Order.**  
> *Nexconn Build Challenge 2026 — Track: Social & Community*

---

## 1. Project Overview

**Society Cart** is a community-driven group grocery purchasing platform built for apartment societies. Instead of individual households placing repetitive, fragmented online orders or making isolated trips to local markets, residents coordinate collective buying through a single shared group chat.

An AI assistant monitors the chat, interprets unstructured, multilingual messages (e.g. English, Telugu, Hindi) and converts them into structured line items. A designated volunteer then aggregates these into one master bulk order, buys at lower wholesale/bulk rates, and distributes the goods flat-by-flat with transparent price sharing.

---

## 2. Problem Statement

1. **High Household Grocery Costs**: Individual apartment households buy smaller packaged units at higher retail prices without bulk discounts.
2. **Duplicated Traffic & Delivery Friction**: Dozens of delivery riders visit the same apartment building daily for trivial items, increasing building security overhead and carbon footprints.
3. **Manual Coordination Fatigue**: When residents attempt community buying through traditional chat apps, order collection is messy, flat numbers are missed, quantities are ambiguous, and billing reconciliation requires hours of manual spreadsheet bookkeeping.

---

## 3. Proposed Solution

Society Cart combines real-time community messaging with AI intelligence and bulk-purchasing workflows:

1. **Community Chat**: Powered by Nexconn Chat Web SDK, giving residents an in-app group channel for their apartment building.
2. **AI Grocery Parser**: Groq-powered LLM extracts line items, quantities, and flat numbers directly from conversational text without rigid forms.
3. **Volunteer Master List**: Automatically combines identical items across flats into a single shopping manifest.
4. **Transparent Billing & Savings**: Calculates per-flat bills from real purchase receipts and displays verified community savings.

---

## 4. Technology Stack

- **Frontend**:
  - React 19
  - Vite 6
  - TypeScript
  - Tailwind CSS v4
  - Lucide React
- **Backend**:
  - Python 3.13
  - FastAPI
  - Uvicorn
  - Pydantic v2 & Pydantic Settings
  - HTTPX
  - PyMongo & dnspython
- **Database**:
  - MongoDB Atlas (Cloud-hosted NoSQL)
- **Messaging**:
  - Nexconn Chat SDK (`@nexconn/chat`, `@nexconn/engine`, `@nexconn/chatui`)
- **AI (Planned Phase 5)**:
  - Groq Cloud API (Llama 3 high-throughput inference)
- **Deployment Targets**:
  - Frontend: Vercel
  - Backend: Render

---

## 5. Project Folder Structure

```
society-cart/
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── .env.example
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── __init__.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   └── NEXCONN_INTEGRATION.md
│
├── .gitignore
├── README.md
└── PROJECT_PROGRESS.md
```

---

## 6. Prerequisites

- **Node.js**: v20.0.0 or newer (tested with v22.15.1)
- **npm**: v10.0.0 or newer (tested with v11.4.2)
- **Python**: 3.11 or newer (tested with 3.13.1)
- **Git**: Installed and configured
- **Ports**: 
  - `5173` available for Frontend Vite Dev Server
  - `8000` available for Backend FastAPI Server

---

## 7. Environment Variables Configuration

Both the frontend and backend require local `.env` files derived from `.env.example`.

### Frontend Configuration (`frontend/.env`)
```bash
cp frontend/.env.example frontend/.env
```
Contents:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_NEXCONN_APP_KEY=your_nexconn_app_key_here
```
> [!IMPORTANT]
> Never put the Nexconn App Secret in a `VITE_` variable. Only public keys belong on the client.

### Backend Configuration (`backend/.env`)
```bash
cp backend/.env.example backend/.env
```
Contents:
```env
APP_ENV=development
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_ORIGIN=http://localhost:5173

MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.example.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=society_cart

NEXCONN_APP_KEY=your_nexconn_app_key_here
NEXCONN_APP_SECRET=your_nexconn_app_secret_here
NEXCONN_API_BASE_URL=https://api.nexconn.ai

GROQ_API_KEY=your_groq_api_key_here
```

---

## 8. Step-by-Step Setup & How to Run

### Frontend Setup & Execution
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the local Vite development server:
   ```bash
   npm run dev
   ```
4. Access the frontend in your browser:
   `http://localhost:5173`
5. To run the production build check:
   ```bash
   npm run build
   ```

### Backend Setup & Execution
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   - On Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - On macOS/Linux:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the FastAPI server with Uvicorn:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
5. Test the API:
   - Root endpoint: `curl http://127.0.0.1:8000/`
   - Health endpoint: `curl http://127.0.0.1:8000/health`
   - Interactive Swagger docs: `http://127.0.0.1:8000/docs`

---

## 9. MongoDB Atlas Setup Guide

Society Cart utilizes MongoDB Atlas for cloud document storage. Follow these steps to prepare your cluster:

1. **Create an Atlas Account & Free Cluster**:
   - Visit [mongodb.com/atlas](https://www.mongodb.com/atlas) and register or sign in.
   - Click **Create Deployment** and choose the **M0 Free Tier** (free forever, 512 MB storage).
   - Select your preferred cloud provider and closest region (e.g., AWS / Mumbai `ap-south-1`).
2. **Create a Database User**:
   - In the Atlas sidebar, navigate to **Security > Database Access**.
   - Click **Add New Database User**.
   - Select **Password Authentication**.
   - Create a username (e.g. `society_cart_user`) and generate a secure password.
   - Assign the user the **Read and write to any database** privilege.
3. **Configure Network Access**:
   - Navigate to **Security > Network Access**.
   - Click **Add IP Address**.
   - For local development, click **Allow Access from Anywhere** (`0.0.0.0/0`) or enter your current public IP address.
4. **Obtain the Connection String**:
   - Go to **Database > Clusters** and click **Connect**.
   - Choose **Drivers** under Connect to your application.
   - Select `Python` and version `3.12 or later`.
   - Copy the SRV connection URI:
     `mongodb+srv://<username>:<password>@cluster0.xxxx.mongodb.net/?retryWrites=true&w=majority`
5. **Configure Backend Environment**:
   - Open `backend/.env` and replace `MONGODB_URI` with your connection string.
   - Replace `<password>` with your database user password.
6. **Why Database Credentials Must Remain Backend-Only**:
   - The connection string contains full administrative credentials to read and modify all data.
   - Frontend web applications bundle and execute JavaScript on untrusted client machines, where inspecting network traffic or memory exposes raw secrets.
   - Only the FastAPI backend should communicate directly with MongoDB Atlas.

---

## 10. Nexconn Integration Preparation

- **Official Console**: [https://console.nexconn.ai/agile/apps/list](https://console.nexconn.ai/agile/apps/list)
- **Detailed Specifications**: See [docs/NEXCONN_INTEGRATION.md](docs/NEXCONN_INTEGRATION.md).
- **Core Packages**: `@nexconn/engine`, `@nexconn/chat`, `@nexconn/chatui`.
- **Integration Plan**:
  - Live messaging and token generation will be implemented in **Phase 3**.
  - Client connections will utilize backend-issued temporary tokens.
  - No fake or mocked chat will be used.

---

## 11. Security Guardrails

- `.gitignore` prevents tracking `.env`, `venv/`, `node_modules/`, and build artifacts.
- `.env.example` templates document variable shapes without revealing secrets.
- CORS is strictly configured to only allow the Vite frontend origin (`http://localhost:5173`).
- No hardcoded API keys or credentials exist in the source code.

---

## 12. Phase 2 Backend & Database Architecture

Phase 2 transforms Society Cart into a data-driven system with MongoDB Atlas, secure auth, and role-based access control:

### Core Database Collections & Indexes

- `users`: Account profiles with bcrypt password hashes, normalized unique emails.
  - Unique Index: `email`
- `societies`: Apartment communities with auto-generated unique invite codes and metadata.
  - Unique Index: `invite_code`
- `memberships`: Connects users to societies and unique apartment flats with roles (`admin`, `volunteer`, `resident`).
  - Compound Partial Unique Index: `(user_id, society_id)` where `is_active: true`
  - Compound Partial Unique Index: `(society_id, flat_number)` where `is_active: true`

### API Endpoints

- **Authentication (`/api/auth`)**:
  - `POST /register`: Registers new user, returns JWT access and refresh tokens.
  - `POST /login`: Validates credentials with bcrypt, returns JWT.
  - `POST /refresh`: Issues a refreshed access token using refresh token.
  - `POST /logout`: Clears auth cookies and session state.
  - `GET /me`: Restores current authenticated user profile and all joined societies.
- **User Management (`/api/users`)**:
  - `GET /me`: Returns active user profile.
  - `PATCH /me`: Safely updates name and phone (forbids updating email, password_hash, or roles).
- **Society Management (`/api/societies`)**:
  - `POST /`: Creates an apartment society, generates 8-char unique invite code, assigns creator as `admin`.
  - `POST /join`: Joins society via invite code & unique flat number (prevents duplicate memberships or occupied flats).
  - `GET /my`: Lists all societies and flat memberships for the authenticated user.
  - `GET /{society_id}`: Gets society details (membership required).
  - `GET /{society_id}/members`: Lists society residents (membership required).
  - `PATCH /{society_id}/members/{membership_id}/role`: Promotes/demotes member between `volunteer` and `resident` (requires society `admin`).

### Automated Test Suite (15 Scenarios)

Run the full automated test suite:
```bash
pytest backend/tests/test_phase2.py -v
```
All 14 test cases covering all 15 scenarios (registration, unique email, login, protected routes, society creation, automatic admin assignment, valid join code, invalid join code, duplicate membership, duplicate flat number, RBAC restrictions, admin volunteer role assignment, cross-society isolation, and protected profile fields) pass with 100% compliance.

---

## 13. Phase 3 Real Nexconn Chat Integration

Phase 3 transitions Society Cart from simulated messaging to real-time group communications powered by the live Nexconn / RongCloud infrastructure:

### Architecture & Security

- **Server-Side Token Minting (`POST /api/chat/token`)**:
  - The client authenticates to FastAPI using standard JWT Bearer tokens.
  - The backend verifies that the requester has an active membership in the target society.
  - The backend mints a user-specific Nexconn session token via the live regional endpoint (`https://api-sg01.ronghub.com/user/getToken.json`) using SHA1 HMAC signatures (`App-Key`, `Nonce`, `Timestamp`, `Signature`).
  - `NEXCONN_APP_SECRET` remains strictly confidential on the backend server and is never exposed to browsers.
  - Non-members or residents from another society are rejected with `HTTP 403 Forbidden`.
- **Automatic Group Channel Lifecycle**:
  - Society creation automatically provisions a distinct group channel: `nexconn_group_id: "society_{society_id}"`.
  - Residents joining a society are automatically synced into the group (`POST /group/join.json`).
  - Members leaving or deactivated are automatically unmapped (`POST /group/quit.json`).
- **System Bot Messaging (`POST /api/chat/system-message`)**:
  - Enables backend-triggered broadcasts (round open/close, order notifications) using `sender_id: "society_cart_bot"`.
- **Frontend Real-time Integration**:
  - Built with `@nexconn/engine@26.5.1` and `@nexconn/chat@26.5.1`.
  - Singleton `NexconnClient` handles connection status tracking (`CONNECTED`, `CONNECTING`, `DISCONNECTED`), message dispatch (`GroupChannel.sendMessage`), and message stream subscription.
  - `ChatContext` enriches raw incoming messages with real apartment resident data (Flat number, Name, Role badge).
  - Preserves the full Phase 1 UI design system, showing a live status indicator (`Nexconn Live`), loading skeletons, and delivery error feedback.

### Verification & Test Suite

Run the Phase 3 automated test suite:
```bash
pytest backend/tests/test_phase3.py -v
```
All test scenarios pass with 100% compliance:
1. `test_chat_token_requires_authentication`: Confirms 401 Unauthorized for unauthenticated requests.
2. `test_chat_token_rejects_non_member`: Confirms 403 Forbidden for non-residents.
3. `test_chat_token_success_for_active_member`: Returns valid Nexconn token and mapped `group_id`.
4. `test_two_residents_get_distinct_tokens_same_group`: Verifies distinct session tokens for different flats mapped to the same group channel.
5. `test_system_message_broadcast`: Confirms backend system bot broadcasts succeed.
6. `test_chat_token_rejects_deactivated_member`: Confirms 403 Forbidden when membership is deactivated.

---

## 14. Phase 4 Grocery Order Rounds

Phase 4 introduces the complete procurement round lifecycle, linking community messaging with structured ordering rounds, strict deadline enforcement, and volunteer logistics:

### MongoDB Collections & Indexes

- **`order_rounds`**:
  - `society_id`: Foreign key referencing `societies._id`.
  - `round_number`: Sequential round number within each apartment society (1, 2, 3...).
  - `status`: `"draft"` | `"open"` | `"closed"` | `"cancelled"`.
  - `deadline_at`: Order cutoff timestamp in UTC.
  - `shopping_date`: Expected procurement date string.
  - `opening_announcement_sent` & `closing_announcement_sent`: State tracking flags to prevent duplicate announcements.
  - **Partial Unique Index (`idx_order_rounds_society_open_unique`)**: `{society_id: 1}` with filter `{"status": "open"}` — strictly prevents more than one open round per society at the database layer.
  - **Query Indexes**: `{society_id: 1, round_number: -1}` and `{status: 1, deadline_at: 1}`.
- **`grocery_submissions`**:
  - `round_id`: Foreign key referencing active `order_rounds._id`.
  - `user_id` & `flat_number`: Submitting resident's account ID and flat number.
  - `message_id`: Real Nexconn message ID returned by SDK upon delivery.
  - `raw_text`: Natural language grocery request.
  - `status`: `"pending"` (ready for Phase 5 AI parsing).
  - **Query Indexes**: `(society_id, round_id)`, `(round_id, flat_number)`, and `message_id`.

### API Endpoints

- **`POST /api/societies/{id}/rounds`**: Create draft round (requires `volunteer` or `admin`). Validates future deadline.
- **`POST /api/societies/{id}/rounds/{round_id}/open`**: Opens round and broadcasts real Nexconn opening announcement. Rejects if another round is already open (409 Conflict).
- **`POST /api/societies/{id}/rounds/{round_id}/close`**: Closes active round and broadcasts real Nexconn closing notice.
- **`GET /api/societies/{id}/rounds/active`**: Fetches current open round (or null). Automatically executes lazy deadline expiration check.
- **`GET /api/societies/{id}/rounds`**: Lists past and present rounds in descending order.
- **`POST /api/societies/{id}/rounds/{round_id}/submissions`**: Associates a resident's Nexconn message with the round. Strictly rejected with HTTP 400 if round is closed, draft, or expired.
- **`GET /api/societies/{id}/rounds/{round_id}/submissions`**: Lists all registered submissions for a given round.

### Automatic Deadline Enforcement

- **Dual-Mechanism Architecture**:
  1. **Background Polling Loop**: A lightweight asyncio task running every 10 seconds detects rounds with `status == "open"` and `deadline_at <= now()`. It atomically closes them and sends the Nexconn closing notification.
  2. **On-Demand Lazy Evaluation**: Any request to `GET /active`, `POST /open`, or `POST /submissions` verifies deadline status and auto-closes expired rounds immediately.

### Verification & Test Suite

Run the Phase 4 automated test suite:
```bash
pytest backend/tests/test_phase4.py -v
```
All 16 required test scenarios across 7 test groups passed with 100% compliance:
- Scenario 1–3: Admin & Volunteer round creation allowed, Resident rejected (403).
- Scenario 4–6: Admin & Volunteer round opening allowed, Resident rejected (403).
- Scenario 7–8: Single active round constraint per society enforced (409 Conflict); separate societies can have simultaneous active rounds.
- Scenario 9–10: Voluntary closure works; reopening closed rounds is blocked (400).
- Scenario 11–12: Expired rounds auto-close; duplicate closure notices prevented.
- Scenario 13: Cross-society access rejected (403 Forbidden).
- Scenario 14–16: Closed rounds reject grocery submissions (400); active round API returns null when closed; round history scoped to society in descending order.

---

## 15. Current Development Status

- **Completed Phases**:
  - Phase 0: Workspace Preparation & Architecture
  - Phase 1: UI Foundation & Application Layout (7 Screens & Design System)
  - Phase 2: Backend, Database & User Management (FastAPI, MongoDB Atlas, JWT, RBAC)
  - Phase 3: Real Nexconn Chat Integration (Live Engine/Chat SDKs, Token Minting, Group Channels, 100% E2E Verified)
  - Phase 4: Grocery Order Rounds (Lifecycle, Deadline Scheduler, Submissions Linking, 100% E2E Verified)
- **Next Phase**: Phase 5 — AI Grocery Understanding
