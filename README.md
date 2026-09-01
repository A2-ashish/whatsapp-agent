# WhatsApp Commerce Platform 🚀

An autonomous, agentic WhatsApp commerce platform designed for small retailers and wholesalers. This platform allows a business to run an AI agent on their WhatsApp Business number to handle product queries, quotes, bulk negotiation, and order creation autonomously—while escalating out-of-bounds requests directly to the human owner via a premium React dashboard.

## 🌟 Key Features

### 🤖 Autonomous WhatsApp Agent
- **LLM-Powered Intelligence**: Driven by the Gemini 2.0 Flash model.
- **Real-Time Data Integration**: Searches live inventory, calculates dynamic bulk discount pricing, and pulls customer history.
- **Safety First (Policy Engine)**: Server-side guardrails prevent the LLM from hallucinating discounts, exceeding max order limits, or selling out-of-stock items.
- **Idempotency & Concurrency**: Uses PostgreSQL advisory locks and idempotency keys to handle rapid or duplicate webhook triggers gracefully.

### 📊 Seller Dashboard
- **Glassmorphism UI**: A premium, responsive interface built with React and Vanilla CSS.
- **Live Updates**: Real-time server-sent events (SSE) for new messages, orders, and escalations.
- **Escalation Handoff**: Review escalations and choose to either manually intervene or provide an instruction to the AI agent to continue the conversation.
- **Full Control**: Manage products, adjust auto-approval limits, define discount tiers, and view full AI/human conversation transcripts.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.14+, FastAPI, SQLAlchemy (Async), Uvicorn, Google GenAI SDK.
- **Database**: PostgreSQL (Asyncpg) + Alembic for migrations.
- **Frontend**: React, Vite, React Router, Axios, Lucide React.
- **Infrastructure**: Docker Compose (Local) / Render Blueprint (Production).
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (Extremely fast Python package installer).

---

## 🚀 Getting Started (Local Development)

### 1. Prerequisites
- Docker & Docker Compose (for PostgreSQL).
- [uv](https://github.com/astral-sh/uv) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- Node.js (v18+) and npm.
- A Google Gemini API Key.

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/A2-ashish/whatsapp-agent.git
cd whatsapp-agent

# Set up environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Start the Platform
You can start the entire platform (Backend, Database, and Frontend Dashboard) with a single command!

**On Windows:**
Double-click `start.bat` or run:
```bash
.\start.bat
```

**On Mac/Linux:**
```bash
chmod +x start.sh
./start.sh
```

This script will automatically:
1. Build and start the backend and PostgreSQL database in Docker.
2. Seed the database with an admin account and sample products.
3. Start the React dashboard.

*The React Dashboard will open at `http://localhost:5173`.*
*The Backend API will run at `http://localhost:8001`.*
*The dashboard will be running at `http://localhost:5173`.*
**Login Credentials:**
- Email: `admin@store.com`
- Password: `admin123`

---

## 🌍 Production Deployment (Render)

This project includes a `render.yaml` Blueprint for 1-click deployment.

1. Fork or push this repository to your GitHub account.
2. Sign in to [Render](https://render.com/).
3. Go to **Blueprints** -> **New Blueprint Instance**.
4. Connect your GitHub repository.
5. Render will automatically provision:
   - A PostgreSQL Database (`whatsapp-commerce-db`)
   - A Python Web Service (`whatsapp-commerce-api`)
   - A Static Site for the Dashboard (`whatsapp-commerce-dashboard`)
6. In the Render Dashboard for the `whatsapp-commerce-api` Web Service, add the required Environment Variables:
   - `GEMINI_API_KEY`
   - `WA_PHONE_NUMBER_ID`
   - `WA_ACCESS_TOKEN`
   - `WA_VERIFY_TOKEN`
   - `WA_APP_SECRET`

---

## 📱 Meta Webhook Configuration
To connect this to a real WhatsApp number:
1. Create a Meta App at [developers.facebook.com](https://developers.facebook.com/).
2. Add the WhatsApp product and configure a phone number.
3. Set your Webhook URL to `https://<YOUR-RENDER-API-URL>/webhook`.
4. Set the Verify Token to match the `WA_VERIFY_TOKEN` in your environment variables.
5. Subscribe to the `messages` webhook field.

---

## 🏗️ Architecture

Read the full technical specification here: [Agent Structure Spec](./agent\ structure.md)
