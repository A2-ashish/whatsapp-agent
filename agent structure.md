# Agent Structure — WhatsApp Commerce Platform

> Deep architectural breakdown of the autonomous WhatsApp commerce agent. This document maps every component, data flow, decision point, and safety mechanism from the moment a customer's WhatsApp message hits the webhook to the final reply (or escalation) being sent back.

---

## 1. HIGH-LEVEL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        WHATSAPP COMMERCE PLATFORM                               │
│                                                                                 │
│  ┌──────────────┐     ┌──────────────────────────────────────────────────────┐  │
│  │   WhatsApp    │     │                   FASTAPI BACKEND                    │  │
│  │   Business    │◄───►│                                                      │  │
│  │   Cloud API   │     │  ┌────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │   (Meta)      │     │  │  Webhook    │  │   Agent     │  │  Dashboard  │   │  │
│  │              │     │  │  Receiver   │──│   Engine    │  │  API        │   │  │
│  └──────────────┘     │  └────────────┘  └──────┬──────┘  └──────┬──────┘   │  │
│                        │                         │                │           │  │
│                        │              ┌──────────┴──────────┐     │           │  │
│                        │              │   TOOL EXECUTOR     │     │           │  │
│                        │              │   + POLICY ENGINE   │     │           │  │
│                        │              └──────────┬──────────┘     │           │  │
│                        │                         │                │           │  │
│                        │              ┌──────────┴────────────────┴──────┐    │  │
│                        │              │         POSTGRESQL DATABASE       │    │  │
│                        │              └──────────────────────────────────┘    │  │
│                        │                                                      │  │
│                        └──────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                     SELLER DASHBOARD (React)                             │   │
│  │   Inventory │ Orders │ Escalations │ Policies │ Conversations │ Analytics│   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Component Summary

| Component | Role | Tech |
|---|---|---|
| **Webhook Receiver** | Ingests WhatsApp messages, deduplicates, routes to Agent Engine | FastAPI endpoint |
| **Agent Engine** | Orchestrates the Gemini tool-calling loop per conversation | Python + Gemini API |
| **Tool Executor** | Implements the 9 agent tools as real database/API operations | Python functions |
| **Policy Engine** | Server-side guardrail validation on every mutating action | Python validation layer |
| **Message Sender** | Sends replies back via WhatsApp Business Cloud API | HTTP client |
| **Dashboard API** | REST + SSE endpoints for the seller's web dashboard | FastAPI routes |
| **Database** | Source of truth for all state | PostgreSQL |
| **Seller Dashboard** | Web UI for inventory, orders, escalations, policies, analytics | React SPA |

---

## 2. DIRECTORY STRUCTURE

```
whatsapp-commerce/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, startup, middleware
│   │   ├── config.py                  # Env vars, secrets, API keys
│   │   │
│   │   ├── db/
│   │   │   ├── database.py            # SQLAlchemy engine, session
│   │   │   ├── models.py              # ORM models (all 8 tables)
│   │   │   └── migrations/            # Alembic migration files
│   │   │
│   │   ├── api/
│   │   │   ├── webhook.py             # POST /webhook — WhatsApp incoming
│   │   │   ├── dashboard/
│   │   │   │   ├── auth.py            # POST /auth/login, /auth/me
│   │   │   │   ├── inventory.py       # CRUD /products
│   │   │   │   ├── orders.py          # GET/PATCH /orders
│   │   │   │   ├── escalations.py     # GET/POST /escalations
│   │   │   │   ├── policies.py        # CRUD /discount-policies
│   │   │   │   ├── conversations.py   # GET /conversations, /messages
│   │   │   │   ├── analytics.py       # GET /analytics
│   │   │   │   └── sse.py             # GET /events — SSE stream
│   │   │   └── health.py              # GET /health
│   │   │
│   │   ├── agent/
│   │   │   ├── engine.py              # Core agentic loop (the brain)
│   │   │   ├── system_prompt.py       # Dynamic system prompt builder
│   │   │   ├── context_builder.py     # Assembles conversation context
│   │   │   ├── tools/
│   │   │   │   ├── registry.py        # Tool registration + Gemini schema
│   │   │   │   ├── inventory.py       # search_inventory
│   │   │   │   ├── customer.py        # get_customer_history
│   │   │   │   ├── pricing.py         # get_discount_policy, calculate_order_total
│   │   │   │   ├── orders.py          # create_order, check_order_status
│   │   │   │   ├── invoice.py         # generate_invoice
│   │   │   │   ├── escalation.py      # escalate_to_owner
│   │   │   │   └── logging.py         # log_action
│   │   │   └── guardrails/
│   │   │       ├── policy_engine.py   # Server-side validation
│   │   │       ├── validators.py      # Individual check functions
│   │   │       └── idempotency.py     # Duplicate order prevention
│   │   │
│   │   ├── whatsapp/
│   │   │   ├── client.py              # Send messages via Cloud API
│   │   │   ├── webhook_parser.py      # Parse incoming webhook payloads
│   │   │   └── message_formatter.py   # Format agent responses for WA
│   │   │
│   │   ├── services/
│   │   │   ├── conversation_service.py  # Conversation lifecycle
│   │   │   ├── customer_service.py      # Customer lookup/creation
│   │   │   ├── order_service.py         # Order business logic
│   │   │   ├── escalation_service.py    # Escalation lifecycle + SSE
│   │   │   └── notification_service.py  # SSE push + optional WA alerts
│   │   │
│   │   └── utils/
│   │       ├── logging.py             # Structured logging
│   │       └── errors.py              # Custom exception classes
│   │
│   ├── tests/
│   │   ├── test_agent_loop.py
│   │   ├── test_guardrails.py
│   │   ├── test_tools.py
│   │   └── test_webhook.py
│   │
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
│
├── dashboard/                          # React SPA
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx          # Analytics home
│   │   │   ├── Inventory.jsx
│   │   │   ├── Orders.jsx
│   │   │   ├── Escalations.jsx
│   │   │   ├── Policies.jsx
│   │   │   ├── Conversations.jsx
│   │   │   └── Login.jsx
│   │   ├── components/
│   │   ├── hooks/
│   │   │   └── useSSE.js              # Real-time event hook
│   │   ├── services/
│   │   │   └── api.js                 # Axios client
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
└── README.md
```

---

## 3. THE AGENT ENGINE — DETAILED BREAKDOWN

This is the core of the platform. It's **not** a simple request-response wrapper around Gemini — it's an agentic loop that can call multiple tools, chain results, and make autonomous decisions across multiple reasoning steps before producing a final response.

### 3.1 Agentic Loop Flow

```
                    ┌─────────────────────────────┐
                    │    INCOMING WHATSAPP MSG     │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │  1. WEBHOOK RECEIVER         │
                    │  - Parse payload             │
                    │  - Deduplicate (msg ID)      │
                    │  - Extract sender + content  │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │  2. CUSTOMER RESOLUTION      │
                    │  - Lookup by whatsapp_number │
                    │  - Create if first contact   │
                    │  - Load or create convo      │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │  3. CONTEXT BUILDER          │
                    │  - Recent N messages         │
                    │  - Customer summary/notes    │
                    │  - Active escalation state   │
                    │  - Pending order state       │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │  4. SYSTEM PROMPT ASSEMBLY   │
                    │  - Base instructions         │
                    │  - Inject: business_name,    │
                    │    product_category,          │
                    │    auto_approve_limit         │
                    │  - Inject: customer context   │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │  5. GEMINI TOOL-CALLING LOOP         │
               │                                      │
               │  ┌────────────────────────────────┐  │
               │  │  Send to Gemini:               │  │
               │  │  - System prompt               │  │
               │  │  - Conversation history        │  │
               │  │  - Tool definitions (9 tools)  │  │
               │  │  - New customer message        │  │
               │  └──────────────┬─────────────────┘  │
               │                 │                     │
               │                 ▼                     │
               │  ┌────────────────────────────────┐  │
               │  │  Gemini responds with either:  │  │
               │  │  A) tool_calls[] → execute     │  │
               │  │  B) text response → done       │  │
               │  └──────────────┬─────────────────┘  │
               │                 │                     │
               │      ┌─────────┴─────────┐           │
               │      ▼                   ▼           │
               │  ┌─────────┐      ┌───────────┐      │
               │  │ TOOL    │      │ FINAL     │      │
               │  │ CALLS   │      │ TEXT      │      │
               │  └────┬────┘      │ RESPONSE  │      │
               │       │           └─────┬─────┘      │
               │       ▼                 │             │
               │  ┌─────────────────┐    │             │
               │  │ TOOL EXECUTOR   │    │             │
               │  │ + POLICY ENGINE │    │             │
               │  │ (server-side    │    │             │
               │  │  validation)    │    │             │
               │  └────────┬────────┘    │             │
               │           │             │             │
               │           ▼             │             │
               │  ┌─────────────────┐    │             │
               │  │ Feed results    │    │             │
               │  │ back to Gemini  │────┘             │
               │  │ (loop again)    │                  │
               │  └─────────────────┘                  │
               │                                      │
               │  Max iterations: 10 (safety cap)     │
               └──────────────┬───────────────────────┘
                              │
                              ▼
               ┌──────────────────────────────────────┐
               │  6. RESPONSE DISPATCH                 │
               │  - Format for WhatsApp               │
               │  - Send via Cloud API                │
               │  - Log message + tool_calls to DB    │
               │  - Update conversation.last_msg_at   │
               └──────────────────────────────────────┘
```

### 3.2 Pseudocode — `engine.py`

```python
class AgentEngine:
    """
    The brain. One instance per incoming message.
    Manages the full Gemini tool-calling loop.
    """

    MAX_ITERATIONS = 10  # Safety cap — prevents runaway loops

    async def process_message(
        self,
        customer: Customer,
        conversation: Conversation,
        seller: Seller,
        incoming_message: str,
    ) -> str:
        # 1. Build context
        context = await self.context_builder.build(
            conversation_id=conversation.id,
            customer_id=customer.id,
            max_messages=20,          # Recent history window
            include_customer_notes=True,
            include_active_escalation=True,
        )

        # 2. Check if conversation is paused (awaiting escalation resolution)
        if context.active_escalation:
            return self._handle_paused_conversation(
                customer, context.active_escalation, incoming_message
            )

        # 3. Assemble the system prompt with seller-specific values
        system_prompt = self.prompt_builder.build(
            business_name=seller.business_name,
            product_category=seller.product_category,
            auto_approve_limit=seller.auto_approve_order_limit,
            customer_context=context.customer_summary,
        )

        # 4. Prepare message history for Gemini
        messages = self._format_history(context.recent_messages)
        messages.append({"role": "user", "content": incoming_message})

        # 5. Enter the agentic loop
        iteration = 0
        while iteration < self.MAX_ITERATIONS:
            iteration += 1

            try:
                response = await self.gemini_client.generate(
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=self.tool_registry.get_schemas(),
                )
            except GeminiAPIError:
                # Graceful degradation — never silence, never raw error
                await self.tools.escalate_to_owner(
                    reason="Gemini API failure",
                    conversation_summary=context.summary,
                    suggested_action="Manual response needed",
                )
                return "Let me check on this and get back to you shortly 🙏"

            # A) Gemini returned tool calls → execute them
            if response.tool_calls:
                tool_results = []
                for call in response.tool_calls:
                    result = await self.tool_executor.execute(
                        tool_name=call.name,
                        arguments=call.arguments,
                        context={
                            "seller_id": seller.id,
                            "customer_id": customer.id,
                            "conversation_id": conversation.id,
                        },
                    )
                    tool_results.append(result)

                    # Log every tool call for audit
                    await self.action_logger.log(
                        seller_id=seller.id,
                        conversation_id=conversation.id,
                        action_type=call.name,
                        details={"args": call.arguments, "result": result},
                    )

                # Feed tool results back into the conversation for next loop
                messages.append({"role": "assistant", "tool_calls": response.tool_calls})
                messages.append({"role": "tool", "results": tool_results})
                continue  # Loop back for Gemini's next decision

            # B) Gemini returned a final text response → we're done
            if response.text:
                return response.text

        # Safety: if we hit MAX_ITERATIONS, escalate
        await self.tools.escalate_to_owner(
            reason="Agent exceeded maximum reasoning steps",
            conversation_summary=context.summary,
            suggested_action="Review conversation — agent may be stuck in a loop",
        )
        return "Let me check with the owner on this one, I'll get back to you shortly 🙏"
```

### 3.3 Context Builder — What Gets Fed to the Agent

The context builder is critical for cost, latency, and agent quality. It assembles a **focused** context window, not the entire conversation history.

```python
class ContextBuilder:
    """
    Assembles the context payload for each agent invocation.
    Balances completeness (agent needs enough to be useful)
    vs. cost/latency (don't send 500 messages every turn).
    """

    async def build(self, conversation_id, customer_id, max_messages=20,
                    include_customer_notes=True, include_active_escalation=True):

        return ConversationContext(
            # Last N messages — enough for conversational continuity
            recent_messages=await self._get_recent_messages(
                conversation_id, limit=max_messages
            ),

            # One-paragraph customer summary (not full history)
            # e.g. "Returning customer. 5 past orders, avg ₹3,200.
            #        Owner note: 'VIP — always give priority'."
            customer_summary=await self._build_customer_summary(customer_id),

            # Is there an open escalation on this conversation?
            # If yes, the agent should know the resolution or pause.
            active_escalation=await self._get_active_escalation(conversation_id),

            # Pending (unconfirmed) order in this conversation, if any
            pending_order=await self._get_pending_order(conversation_id),
        )
```

**Context window strategy:**

| Data | Included | Size Control |
|---|---|---|
| Recent messages | Last 20 messages | Hard cap, oldest trimmed |
| Customer summary | Always | Pre-summarized to ~100 words |
| Customer notes (seller's) | Always | Raw text, typically short |
| Past orders | On-demand via tool | Only when agent calls `get_customer_history` |
| Discount policy | On-demand via tool | Only when agent calls `get_discount_policy` |
| Full conversation | Never auto-loaded | Agent can request via tool if needed |

---

## 4. TOOL DEFINITIONS — GEMINI FUNCTION CALLING SCHEMAS

Each tool is defined both as a **Gemini function-calling schema** (so the LLM knows what's available and how to call it) and as a **Python implementation** (the actual server-side logic).

### 4.1 Tool Registry

```python
# agent/tools/registry.py

TOOL_DEFINITIONS = [
    {
        "name": "search_inventory",
        "description": "Search the live product catalog. Returns matching products with current stock levels and pricing. Always call this before answering availability or price questions — never rely on earlier conversation context for stock data.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query (e.g. 'blue formal shirt size L')"
                },
                "filters": {
                    "type": "object",
                    "description": "Optional structured filters",
                    "properties": {
                        "category": {"type": "string"},
                        "min_price": {"type": "number"},
                        "max_price": {"type": "number"},
                        "size": {"type": "string"},
                        "color": {"type": "string"},
                        "in_stock_only": {"type": "boolean", "default": True}
                    }
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_customer_history",
        "description": "Retrieve a customer's past orders, preferences, and any notes the business owner has added about them. Call at conversation start for personalization.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_discount_policy",
        "description": "Get the current bulk-discount tiers and any active promotions. Must be called before quoting any discounted price — never calculate discounts from memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "seller_id": {"type": "string"}
            },
            "required": ["seller_id"]
        }
    },
    {
        "name": "calculate_order_total",
        "description": "Calculate the final order total with correct pricing and applicable discounts. Always use this instead of doing math yourself. Returns a detailed quote breakdown.",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string"},
                            "quantity": {"type": "integer"}
                        }
                    },
                    "description": "List of items with product IDs and quantities"
                },
                "customer_id": {"type": "string"}
            },
            "required": ["items", "customer_id"]
        }
    },
    {
        "name": "create_order",
        "description": "Commit an order, decrement inventory, and return order ID. ONLY call after the customer has explicitly confirmed the final quoted total. Subject to server-side validation against auto-approval limit, discount policy, and stock availability.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "unit_price": {"type": "number"}
                        }
                    }
                },
                "total": {"type": "number"},
                "notes": {"type": "string", "description": "Any special instructions or context"}
            },
            "required": ["customer_id", "items", "total"]
        }
    },
    {
        "name": "generate_invoice",
        "description": "Generate an invoice for a confirmed order. Returns a formatted invoice text or PDF link.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"}
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "check_order_status",
        "description": "Look up order status. Can search by order ID or customer ID (returns most recent orders).",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "customer_id": {"type": "string"}
            }
        }
    },
    {
        "name": "escalate_to_owner",
        "description": "Hand off the conversation to the business owner. Creates an escalation ticket, pauses the conversation, and notifies the owner in real time. Always include a clear, complete summary so the owner can act without re-reading the thread.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why this is being escalated (e.g. 'discount request beyond policy', 'customer complaint', 'order exceeds auto-approval limit')"
                },
                "conversation_summary": {
                    "type": "string",
                    "description": "Concise summary of the conversation so far — what the customer wants, what's been quoted, what's blocking"
                },
                "suggested_action": {
                    "type": "string",
                    "description": "What the agent recommends the owner do (e.g. 'approve 12% discount on 500 units', 'investigate wrong-size complaint from order #1234')"
                }
            },
            "required": ["reason", "conversation_summary", "suggested_action"]
        }
    },
    {
        "name": "log_action",
        "description": "Log an autonomous action to the audit trail. Call after every quote, discount application, order creation, or escalation. This is mandatory bookkeeping.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action type (e.g. 'quote_given', 'order_created', 'discount_applied', 'escalation_triggered')"
                },
                "details": {
                    "type": "object",
                    "description": "Structured details about the action"
                }
            },
            "required": ["action", "details"]
        }
    }
]
```

### 4.2 Tool Execution Flow

```
Agent calls tool
       │
       ▼
┌─────────────────────────────┐
│     TOOL EXECUTOR           │
│                             │
│  1. Validate tool name      │
│  2. Inject context          │
│     (seller_id, customer_id,│
│      conversation_id)       │
│  3. Route to implementation │
└──────────────┬──────────────┘
               │
    ┌──────────┴──────────────────────┐
    │                                  │
    ▼                                  ▼
┌──────────────┐            ┌──────────────────┐
│ READ-ONLY    │            │ MUTATING TOOLS   │
│ TOOLS        │            │ (write to DB)    │
│              │            │                  │
│ search_inv.  │            │ create_order     │
│ get_history  │            │ escalate_to_owner│
│ get_policy   │            │ log_action       │
│ calc_total   │            │ generate_invoice │
│ check_status │            │                  │
│              │            │  ┌────────────┐  │
│ (no guardrail│            │  │ POLICY     │  │
│  needed)     │            │  │ ENGINE     │  │
│              │            │  │ (validate  │  │
│              │            │  │  BEFORE    │  │
│              │            │  │  commit)   │  │
│              │            │  └────────────┘  │
└──────────────┘            └──────────────────┘
```

---

## 5. POLICY ENGINE — SERVER-SIDE GUARDRAILS

> **Core principle**: The LLM prompt says "don't exceed limits." The Policy Engine _enforces_ it. The prompt is guidance; the engine is law.

### 5.1 Validation Architecture

```python
# agent/guardrails/policy_engine.py

class PolicyEngine:
    """
    Server-side enforcement layer. Sits between the agent's tool calls
    and actual database mutations. Every create_order call passes through
    here BEFORE anything is committed.

    If validation fails, the tool call is REJECTED and the agent receives
    an error result forcing it to escalate or adjust.
    """

    async def validate_order_creation(
        self, seller_id: str, customer_id: str, items: list, total: float
    ) -> PolicyResult:

        checks = [
            self._check_order_limit(seller_id, total),
            self._check_discount_compliance(seller_id, items),
            self._check_stock_availability(items),
            self._check_idempotency(customer_id, items),
        ]

        results = await asyncio.gather(*checks)

        for result in results:
            if not result.passed:
                return PolicyResult(
                    approved=False,
                    violation=result.violation,
                    required_action="escalate",
                    details=result.details,
                )

        return PolicyResult(approved=True)
```

### 5.2 Individual Checks

| Check | What It Validates | On Failure |
|---|---|---|
| **Order Limit** | `total ≤ seller.auto_approve_order_limit` | Force escalation — "order exceeds auto-approval limit" |
| **Discount Compliance** | Applied discount ≤ applicable tier from `discount_policy` for the given quantity | Reject — recalculate with correct discount or escalate |
| **Stock Availability** | `requested_qty ≤ product.stock_quantity` for every line item | Reject — agent told to inform customer and suggest alternatives |
| **Idempotency** | No identical order (same customer + same items + same total) created in the last 5 minutes | Reject — return existing order_id instead of creating duplicate |

### 5.3 Idempotency Implementation

```python
# agent/guardrails/idempotency.py

class IdempotencyGuard:
    """
    Prevents duplicate orders from:
    - Customer confirming twice ("yes" "yes")
    - WhatsApp webhook retries (Meta retries on 5xx)
    - Agent loop calling create_order multiple times

    Uses a composite hash of (customer_id, items, total) checked
    against a sliding 5-minute window.
    """

    async def check(self, customer_id: str, items: list, total: float) -> bool:
        order_hash = self._compute_hash(customer_id, items, total)

        recent_order = await self.db.query(
            """SELECT id FROM orders
               WHERE idempotency_hash = :hash
               AND created_at > NOW() - INTERVAL '5 minutes'""",
            {"hash": order_hash}
        )

        if recent_order:
            return IdempotencyResult(
                is_duplicate=True,
                existing_order_id=recent_order.id
            )

        return IdempotencyResult(is_duplicate=False)
```

---

## 6. ESCALATION FLOW — DETAILED SEQUENCE

Escalation is the most architecturally complex flow because it bridges the agent (async, WhatsApp) with the seller (sync, dashboard) and then routes back.

### 6.1 Escalation Lifecycle

```
                     AGENT LOOP
                         │
                         ▼
              ┌─────────────────────┐
              │ escalate_to_owner() │
              │ called by Gemini    │
              └──────────┬──────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌─────────────┐ ┌──────────┐ ┌──────────────┐
   │ Create      │ │ Push SSE │ │ Optional:    │
   │ escalations │ │ event to │ │ WA/SMS alert │
   │ row in DB   │ │ dashboard│ │ to seller's  │
   │ status=open │ │          │ │ phone        │
   └─────────────┘ └──────────┘ └──────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Agent tells customer│
              │ "Checking with      │
              │  owner, will get    │
              │  back to you"       │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ CONVERSATION PAUSED │
              │ (flagged in context)│
              └──────────┬──────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
  ┌──────────────────┐    ┌──────────────────────┐
  │ SELLER OPTION A  │    │ SELLER OPTION B      │
  │ Direct reply     │    │ Instruct the agent   │
  │                  │    │                      │
  │ Types a message  │    │ Types an instruction │
  │ in dashboard →   │    │ e.g. "approve 12%    │
  │ sent directly to │    │ discount" →          │
  │ customer via WA  │    │ agent resumes with   │
  │                  │    │ this guidance and    │
  │ Seller is now    │    │ continues the convo  │
  │ "in the chat"    │    │ autonomously         │
  └──────────────────┘    └──────────────────────┘
            │                         │
            ▼                         ▼
  ┌──────────────────────────────────────┐
  │ Mark escalation resolved             │
  │ Record resolution_notes              │
  │ Unpause conversation                 │
  └──────────────────────────────────────┘
```

### 6.2 Paused Conversation Handling

When a customer messages while their conversation is paused (awaiting escalation resolution):

```python
def _handle_paused_conversation(self, customer, escalation, new_message):
    """
    Don't run the full agent loop.
    Acknowledge the message and reassure the customer.
    Optionally forward the new message to the seller as an update.
    """
    # Update escalation with the new message context
    await self.escalation_service.add_customer_followup(
        escalation_id=escalation.id,
        message=new_message,
    )

    # Notify seller that the customer sent a follow-up
    await self.notification_service.push_sse(
        seller_id=escalation.seller_id,
        event="escalation_followup",
        data={"escalation_id": escalation.id, "message": new_message},
    )

    return "I'm still waiting to hear back from the owner on your request — I'll update you as soon as I have an answer 🙏"
```

---

## 7. SYSTEM PROMPT ASSEMBLY

The system prompt is **not static** — it's assembled at runtime with seller-specific and customer-specific data injected.

### 7.1 Prompt Template Flow

```python
# agent/system_prompt.py

class SystemPromptBuilder:
    """
    Constructs the complete system prompt for each conversation turn.
    Injects seller config + customer context into the base template.
    """

    BASE_TEMPLATE = """
    {agent_instruction_content}
    """
    # ↑ This is the full content from `agent instruction.md`
    #   with {{BUSINESS_NAME}}, {{PRODUCT_CATEGORY}},
    #   and {{AUTO_APPROVE_ORDER_LIMIT}} as template vars

    def build(
        self,
        business_name: str,
        product_category: str,
        auto_approve_limit: float,
        customer_context: str,
    ) -> str:
        prompt = self.BASE_TEMPLATE.replace(
            "{{BUSINESS_NAME}}", business_name
        ).replace(
            "{{PRODUCT_CATEGORY}}", product_category
        ).replace(
            "{{AUTO_APPROVE_ORDER_LIMIT}}", str(auto_approve_limit)
        )

        # Append customer-specific context as an addendum
        if customer_context:
            prompt += f"""

## CURRENT CUSTOMER CONTEXT
{customer_context}
"""

        return prompt
```

### 7.2 Dynamic Injection Sources

| Template Variable | Source | Example |
|---|---|---|
| `{{BUSINESS_NAME}}` | `sellers.business_name` | "Kumar Textiles" |
| `{{PRODUCT_CATEGORY}}` | `sellers.product_category` (or derived) | "fabrics and garments" |
| `{{AUTO_APPROVE_ORDER_LIMIT}}` | `sellers.auto_approve_order_limit` | "25000" |
| Customer context | Built by `ContextBuilder` | "Returning customer, 5 past orders, avg ₹3,200. Owner note: 'VIP'" |

---

## 8. WHATSAPP INTEGRATION LAYER

### 8.1 Webhook Flow

```
Meta Cloud API
      │
      │  POST /webhook  (verification + message events)
      ▼
┌─────────────────────────────────┐
│  webhook.py                     │
│                                 │
│  1. Verify webhook signature    │
│     (X-Hub-Signature-256)       │
│                                 │
│  2. Parse message event         │
│     - Extract: sender phone,    │
│       message text, message ID, │
│       timestamp                 │
│                                 │
│  3. Deduplicate by message ID   │
│     (Meta retries on 5xx)       │
│                                 │
│  4. Enqueue for processing      │
│     (or process inline for v1)  │
│                                 │
│  5. Return 200 immediately      │
│     (Meta expects fast ack)     │
└─────────────────┬───────────────┘
                  │
                  ▼
          AgentEngine.process_message()
                  │
                  ▼
┌─────────────────────────────────┐
│  whatsapp/client.py             │
│                                 │
│  send_text_message(             │
│    phone_number,                │
│    message_text                 │
│  )                              │
│                                 │
│  POST https://graph.facebook    │
│  .com/v18.0/{phone_id}/messages │
│  Authorization: Bearer {token}  │
│  Body: {                        │
│    messaging_product: "whatsapp"│
│    to: phone_number             │
│    text: { body: message }      │
│  }                              │
└─────────────────────────────────┘
```

### 8.2 Message Types Handled

| Incoming | Handling |
|---|---|
| Text message | Full agent loop |
| Image/media | Store reference, treat as text context ("customer sent an image") |
| Location | Extract coordinates, pass to agent as text |
| Status updates (delivered, read) | Update message status in DB, no agent action |

---

## 9. REAL-TIME DASHBOARD UPDATES (SSE)

### 9.1 Event Stream Architecture

```
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  Agent Loop  │        │  Dashboard   │        │   Seller's   │
│  (backend)   │──SSE──►│  API (SSE)   │──SSE──►│   Browser    │
│              │        │              │        │   (React)    │
└──────────────┘        └──────────────┘        └──────────────┘
```

### 9.2 Event Types

```python
SSE_EVENTS = {
    "new_escalation":       # New escalation created — show alert
    "escalation_followup":  # Customer sent follow-up while paused
    "new_order":            # Order created by agent
    "order_status_change":  # Order status updated (by agent or seller)
    "low_stock_alert":      # Stock fell below threshold
    "new_conversation":     # First-time customer contact
    "new_message":          # New message in any conversation
}
```

### 9.3 Dashboard SSE Hook (React)

```javascript
// dashboard/src/hooks/useSSE.js

function useSSE(sellerId) {
    const [events, setEvents] = useState([]);

    useEffect(() => {
        const source = new EventSource(`/api/events?seller_id=${sellerId}`);

        source.addEventListener("new_escalation", (e) => {
            const data = JSON.parse(e.data);
            // Show notification toast
            // Update escalation list
            // Play alert sound
        });

        source.addEventListener("new_order", (e) => {
            const data = JSON.parse(e.data);
            // Update order list
            // Update analytics counters
        });

        return () => source.close();
    }, [sellerId]);

    return events;
}
```

---

## 10. DATA FLOW DIAGRAMS — KEY SCENARIOS

### 10.1 Simple Product Inquiry

```
Customer: "Blue shirt size L hai kya?"
    │
    ▼
[Webhook] → [Agent Engine]
    │
    ├─ Gemini decides: call search_inventory("blue shirt size L")
    │
    ├─ Tool returns: [{name: "Premium Blue Formal", price: 1299, stock: 15, ...}]
    │
    ├─ Gemini gets results, generates response
    │
    ├─ Gemini decides: call log_action("product_inquiry", {...})
    │
    ▼
Agent: "Haan, Premium Blue Formal ₹1299 mein available hai, size L stock mein hai. Photo bhejun?"
```

**Tool calls: 2** (search_inventory, log_action)
**Gemini iterations: 2** (tool call round, then final response)

### 10.2 Bulk Order Negotiation (Multi-Step)

```
Customer: "200 blue shirts ka bulk rate kya hoga?"
    │
    ▼
Iteration 1:
├─ Gemini: search_inventory("blue shirt") → finds products
├─ Gemini: get_discount_policy(seller_id) → gets tiers
│
Iteration 2:
├─ Gemini: calculate_order_total(items=[{blue_shirt, qty=200}]) → ₹198,000 (₹990/pc after 15% bulk)
│
Iteration 3:
├─ Gemini: log_action("bulk_quote_given") + generates response
│
Agent: "200 pieces pe ₹990/piece hoga, total ₹1,98,000. Confirm karu?"
    │
Customer: "Thoda aur kam karo"
    │
Iteration 4:
├─ Gemini: checks discount policy → max tier already applied
│
Iteration 5:
├─ Gemini: escalate_to_owner(reason="customer requesting beyond-policy discount",
│    summary="Customer wants 200 blue shirts, quoted ₹990/pc (15% tier), asking for more",
│    suggested_action="Consider 18% for 200+ units, would be ₹975/pc")
│
Agent: "Isse zyada discount ke liye owner se check karna padega, ek minute 🙏"
    │
[CONVERSATION PAUSED — awaiting seller resolution]
```

**Tool calls: 7** across 5 iterations
**Demonstrates**: Multi-step reasoning, policy-aware negotiation, principled escalation

### 10.3 Escalation → Seller Resolution → Agent Resume

```
[Seller sees escalation on dashboard]
    │
    ├─ Option A: Types "Tell them ₹975/pc is final, 18% discount approved for this order"
    │
    ▼
[System]: Marks escalation resolved, injects seller's instruction into conversation context
    │
    ▼
[Agent Engine resumes]: Gemini sees the seller's instruction in context
    │
    ├─ Gemini: calculate_order_total(items, discount_override=18%) → ₹1,95,000
    │
    ├─ Gemini: generates response using seller's guidance
    │
    ▼
Agent (to customer): "Owner ne approve kar diya — ₹975/piece pe 200 pieces, total ₹1,95,000. Confirm karu?"
    │
Customer: "Done, confirm karo"
    │
    ├─ Gemini: create_order(...) → [Policy Engine validates → PASS] → order created
    ├─ Gemini: generate_invoice(order_id) → invoice generated
    ├─ Gemini: log_action("order_created", {...})
    │
    ▼
Agent: "Order confirmed! 🎉 Order #1847. Invoice bhej raha hoon..."
```

---

## 11. ERROR HANDLING & GRACEFUL DEGRADATION

### 11.1 Failure Matrix

| Failure | Detection | Agent Behavior | System Action |
|---|---|---|---|
| Gemini API timeout | HTTP timeout (30s) | "Let me check and get back to you 🙏" | Auto-escalation created |
| Gemini API error (5xx) | HTTP status code | Same polite hold message | Auto-escalation + retry queue |
| Gemini returns nonsensical tool call | Tool executor catches invalid args | Agent receives error result, retries | Logged to `agent_action_log` |
| Tool execution fails (DB error) | Exception in tool implementation | Agent told "tool unavailable" | Auto-escalation + error alert |
| Policy Engine rejects `create_order` | PolicyResult.approved = False | Agent receives rejection reason | Forced escalation with violation details |
| Max iterations exceeded | Loop counter ≥ 10 | Polite hold + escalation | Auto-escalation flagged as "loop detected" |
| WhatsApp send failure | Cloud API error response | Message queued for retry | Retry with exponential backoff |
| Webhook receives duplicate msg | Message ID check | Ignore silently | No processing |

### 11.2 The "Never Silence" Principle

```python
# Every code path that could fail has a fallback message

@contextmanager
async def safe_agent_execution(customer_phone, conversation_id, seller_id):
    try:
        yield
    except Exception as e:
        # Log the full error internally
        logger.error(f"Agent execution failed: {e}", exc_info=True)

        # Customer ALWAYS gets a response
        await whatsapp_client.send_text(
            customer_phone,
            "I'm having a little trouble right now — let me check and get back to you shortly 🙏"
        )

        # Seller ALWAYS gets notified
        await escalation_service.create_auto_escalation(
            seller_id=seller_id,
            conversation_id=conversation_id,
            reason=f"System error: {type(e).__name__}",
            details=str(e),
        )
```

---

## 12. DATABASE RELATIONSHIPS

```
┌──────────┐       ┌──────────────┐       ┌──────────────┐
│  sellers │───┐   │   products   │       │  discount_   │
│          │   │   │              │       │  policy      │
│  id (PK) │   │   │  seller_id   │───┐   │              │
│          │   │   │  (FK)        │   │   │  seller_id   │───┐
└──────────┘   │   └──────────────┘   │   │  (FK)        │   │
               │                      │   └──────────────┘   │
               │   ┌──────────────┐   │                      │
               ├──►│  customers   │   │                      │
               │   │              │   │                      │
               │   │  seller_id   │   │                      │
               │   │  (FK)        │   │                      │
               │   └──────┬───────┘   │                      │
               │          │           │                      │
               │   ┌──────┴───────┐   │                      │
               │   │ conversations│   │                      │
               │   │              │   │                      │
               │   │ customer_id  │   │                      │
               │   │ seller_id    │───┘                      │
               │   └──────┬───────┘                          │
               │          │                                  │
               │   ┌──────┴───────┐                          │
               │   │  messages    │                          │
               │   │              │                          │
               │   │ conversation │                          │
               │   │ _id (FK)     │                          │
               │   └──────────────┘                          │
               │                                             │
               │   ┌──────────────┐                          │
               ├──►│   orders     │                          │
               │   │              │                          │
               │   │  seller_id   │                          │
               │   │  customer_id │                          │
               │   └──────────────┘                          │
               │                                             │
               │   ┌──────────────┐                          │
               ├──►│ escalations  │                          │
               │   │              │                          │
               │   │ seller_id    │                          │
               │   │ customer_id  │                          │
               │   │ conversation │                          │
               │   │ _id (FK)     │                          │
               │   └──────────────┘                          │
               │                                             │
               │   ┌──────────────┐                          │
               └──►│ agent_action │                          │
                   │ _log         │                          │
                   │              │                          │
                   │ seller_id    │                          │
                   │ conversation │                          │
                   │ _id (FK)     │                          │
                   └──────────────┘                          │
                                                             │
                        All FK arrows ──────────────────────►│
                        point back to sellers                │
```

### Additional Schema Notes (beyond `prompt.md`)

| Table | Additional Column | Purpose |
|---|---|---|
| `orders` | `idempotency_hash` | Composite hash for duplicate prevention |
| `orders` | `conversation_id` | Links order to the conversation that created it |
| `conversations` | `is_paused` | Flag for escalation-paused conversations |
| `conversations` | `paused_escalation_id` | Which escalation caused the pause |
| `messages` | `message_wa_id` | WhatsApp message ID for deduplication |
| `sellers` | `product_category` | Used in system prompt template |
| `sellers` | `wa_phone_number_id` | Meta's phone number ID for API calls |
| `sellers` | `wa_access_token` | Encrypted token for Cloud API auth |

---

## 13. SECURITY CONSIDERATIONS

| Concern | Mitigation |
|---|---|
| **Prompt injection via customer messages** | Policy Engine validates all mutations server-side regardless of what the LLM decides. LLM can be tricked into calling `create_order` with bad params, but the Policy Engine will reject it. |
| **WhatsApp webhook spoofing** | Verify `X-Hub-Signature-256` header against app secret on every webhook request. |
| **Seller dashboard auth** | JWT-based auth with httpOnly cookies. Rate-limit login attempts. |
| **Sensitive data in tool call logs** | `tool_calls_json` may contain customer data — scope dashboard access per seller. Encrypt at rest. |
| **API key exposure** | Gemini API key, WhatsApp tokens stored as env vars, never in code or DB. |
| **Rate limiting** | Rate-limit incoming webhook processing per phone number to prevent abuse. |

---

## 14. MONITORING & OBSERVABILITY

### Key Metrics to Track

| Metric | Source | Purpose |
|---|---|---|
| **Autonomy rate** | `orders WHERE no_escalation / total_orders` | Core value metric — % of orders completed without human intervention |
| **Avg tool calls per conversation** | `agent_action_log` | Agent efficiency |
| **Escalation rate** | `escalations.count / conversations.count` | Are policies set correctly? |
| **Avg escalation resolution time** | `escalations.resolved_at - created_at` | Seller responsiveness |
| **Gemini API latency** | Instrumented in `engine.py` | Performance monitoring |
| **Gemini API error rate** | Error counts in `engine.py` | Reliability monitoring |
| **Order creation success rate** | Policy Engine pass/fail ratio | Are guardrails too tight? |
| **Messages per order** | `messages.count / orders.count` | Conversation efficiency |

---

## 15. RELATIONSHIP TO EXISTING FILES

| File | Role in Architecture |
|---|---|
| [prompt.md](file:///c:/Users/a2ash/OneDrive/Desktop/whatsapp/prompt.md) | Full system spec — database schema, tech stack, feature requirements, build order. This agent structure document is the architectural deep-dive that complements it. |
| [agent instruction.md](file:///c:/Users/a2ash/OneDrive/Desktop/whatsapp/agent%20instruction.md) | The actual system prompt template fed to Gemini at runtime. Defines the agent's personality, authority boundaries, tool usage rules, and behavioral examples. Loaded by `SystemPromptBuilder` with template variables injected per seller. |
| [idea.md](file:///c:/Users/a2ash/OneDrive/Desktop/whatsapp/idea.md) | Project ideation notes (currently empty — can be used to capture learnings and pivot ideas during development). |

---

## 16. WHAT MAKES THIS AN "AGENT" (NOT A CHATBOT)

| Property | Chatbot | This Agent |
|---|---|---|
| **Decision making** | Fixed flows / intent classification | Multi-step reasoning with tool use |
| **Data access** | Pre-loaded static answers | Live database queries per turn |
| **Actions** | Sends messages | Creates orders, decrements inventory, generates invoices |
| **Self-awareness of limits** | N/A | Knows its authority boundary and escalates |
| **Audit trail** | Chat logs | Full tool-call trace with arguments and results |
| **Safety** | Prompt rules | Server-side Policy Engine validates every mutation |
| **Learning from seller** | N/A | Incorporates seller instructions post-escalation to resume autonomously |
| **Negotiation** | Scripted responses | Multi-turn reasoning: check policy → quote → counter → re-check → confirm or escalate |
