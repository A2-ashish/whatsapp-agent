# Build Prompt: Agentic WhatsApp Commerce Platform for Small Retailers/Wholesalers

Use this as a spec to hand to a coding assistant (Claude Code, etc.) or to build from yourself, section by section. It covers the full system: the autonomous WhatsApp agent, the backend, the database, and the seller dashboard.

---

## 1. PROJECT SUMMARY

Build a platform that lets a small retail/wholesale business run an AI agent on their WhatsApp Business number. Customers message the number directly; the agent handles product questions, quotes, bulk negotiation, and order creation autonomously within defined limits, and escalates anything outside its authority to the seller. The seller manages everything — inventory, orders, escalations, policies — through a web dashboard.

Two user types:
- **Customer**: interacts only via WhatsApp, never sees the dashboard
- **Seller (business owner)**: uses the web dashboard to manage inventory, view/process orders, handle escalations, and configure the agent's policies

---

## 2. TECH STACK

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **LLM**: Gemini (function calling / tool use)
- **WhatsApp channel**: WhatsApp Business Cloud API (Meta), webhook-based
- **Dashboard frontend**: React (or your preferred framework) — a separate web app calling the FastAPI backend
- **Real-time updates**: Server-Sent Events (SSE) or WebSockets for live order/escalation updates on the dashboard (you've built this pattern before)
- **Auth**: Simple seller login (email/password or magic link) — this is single-tenant per deployment to start, so auth can be minimal (one seller account per instance), but design the schema so multi-tenant is possible later

---

## 3. DATABASE SCHEMA (core tables)

```
sellers
  id, business_name, phone_number (WhatsApp business number), email, password_hash,
  auto_approve_order_limit, created_at

products
  id, seller_id, name, category, description, price, size, color, sku,
  stock_quantity, image_url, is_active, created_at, updated_at

discount_policy
  id, seller_id, min_quantity, max_quantity, discount_percent, active_from, active_to

customers
  id, seller_id, whatsapp_number, name (nullable until known), created_at,
  notes (free text — owner can add manual notes like "always pays late" or "VIP")

conversations
  id, customer_id, seller_id, started_at, last_message_at, status (active/closed)

messages
  id, conversation_id, sender (customer/agent/owner), content, timestamp,
  tool_calls_json (nullable — log of what the agent called, for debugging/audit)

orders
  id, seller_id, customer_id, status (pending/confirmed/processing/shipped/completed/cancelled),
  items_json, subtotal, discount_applied, total, notes, created_at, updated_at

escalations
  id, seller_id, customer_id, conversation_id, reason, conversation_summary,
  suggested_action, status (open/resolved), created_at, resolved_at, resolution_notes

agent_action_log
  id, seller_id, conversation_id, action_type, details_json, timestamp
```

---

## 4. THE AGENT — BEHAVIOR SPEC

### 4.1 Conversation flow
1. Customer messages the WhatsApp number → webhook receives it → look up or create `customer` + `conversation` record
2. Load conversation history + customer notes/history for context
3. Run the Gemini tool-calling loop (see system prompt below) — the agent decides which tools to call, in what order, however many times needed, until it has a final response or needs to escalate
4. Send the agent's reply back via WhatsApp Cloud API
5. Log every tool call and decision to `agent_action_log` and `messages`

### 4.2 Tools the agent can call
Define these as Gemini function-calling tools:

- `search_inventory(query: str, filters: dict)` → returns matching products with live stock/price
- `get_customer_history(customer_id: str)` → past orders, notes, preferences
- `get_discount_policy(seller_id: str)` → current tiers/promotions
- `calculate_order_total(items: list, customer_id: str)` → applies pricing + discount, returns quote
- `create_order(customer_id: str, items: list, total: float, notes: str)` → commits order, decrements stock, returns order_id
- `generate_invoice(order_id: str)` → returns invoice text/PDF link to send
- `check_order_status(order_id: str = None, customer_id: str = None)` → status lookup
- `escalate_to_owner(reason: str, conversation_summary: str, suggested_action: str)` → creates an `escalations` row, notifies seller (push/SSE to dashboard, optionally also a WhatsApp/SMS alert to the seller's own phone)
- `log_action(action: str, details: dict)` → writes to `agent_action_log`

### 4.3 Authority boundaries (enforce server-side, not just in the prompt)
Never trust the LLM alone to enforce limits — validate every `create_order` call server-side against:
- Order total ≤ seller's `auto_approve_order_limit`
- Discount applied ≤ the active `discount_policy` tier for that quantity
- Requested stock ≤ available `stock_quantity`

If any check fails server-side even though the agent tried to proceed, reject the tool call and force an escalation — this is your safety net against prompt injection or model error, same principle as your Razorpay Policy Engine.

### 4.4 The agent system prompt
Use the full system prompt drafted earlier (WhatsApp Business Agent prompt) — fill in the seller's business name, product category, and order limit dynamically per seller from the `sellers` table when you construct the prompt at runtime.

### 4.5 Escalation delivery
When `escalate_to_owner` is called:
- Create the `escalations` row
- Push a real-time update to the dashboard (SSE/WebSocket)
- Optionally send the seller a WhatsApp/SMS alert if they're not actively watching the dashboard
- The agent tells the customer it's checking with the owner and pauses that thread until the seller responds (either resolves it themselves in the dashboard, or provides an instruction the agent should relay)

---

## 5. THE SELLER DASHBOARD — FEATURE SPEC

### 5.1 Inventory management
- Table view of all products: name, category, price, stock, active/inactive toggle
- Add/edit/delete product form (name, category, description, price, size, color, SKU, stock quantity, image upload)
- Bulk import via CSV (nice-to-have, not required for v1)
- Low-stock warning indicator

### 5.2 Order management
- List of all orders with status filter (pending / confirmed / processing / shipped / completed / cancelled)
- Order detail view: customer info, items, pricing, discount applied, notes, full conversation transcript that led to the order
- Seller can update order status (mark shipped, completed, cancelled) — this should sync back so the agent can answer status questions accurately
- Search/filter by customer, date range, status

### 5.3 Escalations (the most important screen)
- Real-time list of open escalations, newest first, with a clear visual alert for new ones
- Each escalation shows: reason, AI's summary of the conversation, AI's suggested action, and a link to the full conversation transcript
- Seller can respond in two ways:
  - **Resolve directly with the customer** by typing a reply that gets sent via WhatsApp (dashboard acts as a manual override channel)
  - **Give the agent an instruction** ("approve this discount", "reject, offer 5% instead") which the agent then uses to continue the conversation autonomously
- Mark resolved once handled

### 5.4 Discount policy configuration
- Simple form: quantity tiers → discount percentage (e.g., 50-99 units: 5%, 100-199: 8%, 200+: 12%)
- Order-value auto-approval limit (the ₹ threshold above which everything escalates)
- Active promotions (optional override, e.g., festival sale)

### 5.5 Conversations view
- List of all customer conversations, searchable, with status (active/closed)
- Full transcript view including which tools the agent called at each step (useful for the seller to trust/audit the agent, and for you to debug during development)

### 5.6 Dashboard home / analytics (nice-to-have for v1, valuable for pitching)
- Orders today/this week, revenue, open escalations count, top products, agent autonomy rate (% of orders closed without escalation) — this last metric is a great one to show off since it quantifies the agent's value

---

## 6. BUILD ORDER (suggested, fits ~6-8 weeks)

**Week 1-2 — Core backend + agent loop**
- DB schema + FastAPI models
- Gemini tool-calling loop with the 9 tools above (start with mocked/manual test messages, no WhatsApp yet)
- Server-side guardrail validation on `create_order`

**Week 3 — WhatsApp integration**
- Meta WhatsApp Business Cloud API webhook setup
- Message send/receive wired to the agent loop
- Conversation/customer creation on first contact

**Week 4-5 — Seller dashboard**
- Inventory CRUD screens
- Order list + detail + status update
- Escalations screen with real-time updates (SSE) and the two response modes

**Week 6 — Policy config + conversations view + analytics**
- Discount policy form
- Conversation transcript viewer
- Basic analytics screen

**Week 7-8 — Pilot + hardening**
- Run it on your own family's business's real WhatsApp number
- Fix edge cases that show up with real customers (ambiguous requests, typos, mixed-language messages)
- Add whatever guardrail you find missing from real usage — this is the most valuable week for your story/demo

---

## 7. THINGS TO GET RIGHT (don't skip these)

- **Idempotency on order creation** — a customer confirming twice, or a webhook retry, should never create duplicate orders
- **Server-side enforcement of every guardrail** — never rely on the prompt alone to keep the agent in bounds
- **Full audit trail** — every tool call logged, so you can show "here's exactly what the agent did and why" — this is your strongest demo material
- **Graceful degradation** — if Gemini API fails or times out, the customer should get a polite "let me check and get back to you" and an escalation, never silence or an error message
- **Conversation context window** — decide how much history to feed the agent per turn (recent messages + customer summary, not the entire history every time, for cost/latency)

---

## 8. WHAT TO EMPHASIZE WHEN YOU PRESENT THIS

- It's not a chatbot — show the tool-call log for a real multi-step negotiation as proof
- The server-side Policy Engine (separate from the LLM) mirrors what you already built for Razorpay — reuse that credibility
- The autonomy-rate metric (% of conversations resolved without human escalation) is your single best "proof it works" number once you have pilot data