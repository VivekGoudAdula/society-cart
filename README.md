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

## 12. Current Development Status

- **Phase**: Phase 0 — Workspace Preparation & Architecture (**Completed**)
- **Next Phase**: Phase 1 — UI Foundation & Application Layout (Awaiting User Sign-off)
