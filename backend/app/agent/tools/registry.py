"""
Tool Registry — Defines all 9 tools as Gemini function-calling schemas
and provides the dispatch map for execution.
"""

from google.genai import types


# ─── Gemini Function Declarations ──────────────────────────────────────

TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="search_inventory",
        description="Search the live product catalog. Returns matching products with current stock levels and pricing. Always call this before answering availability or price questions.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(type="STRING", description="Natural language search query (e.g. 'blue formal shirt size L')"),
                "filters": types.Schema(
                    type="OBJECT",
                    description="Optional structured filters",
                    properties={
                        "category": types.Schema(type="STRING"),
                        "min_price": types.Schema(type="NUMBER"),
                        "max_price": types.Schema(type="NUMBER"),
                        "size": types.Schema(type="STRING"),
                        "color": types.Schema(type="STRING"),
                        "in_stock_only": types.Schema(type="BOOLEAN"),
                    },
                ),
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_customer_history",
        description="Retrieve a customer's past orders, preferences, and owner notes. Call at conversation start for personalization.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "customer_id": types.Schema(type="STRING"),
            },
            required=["customer_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_discount_policy",
        description="Get current bulk-discount tiers and active promotions. Must be called before quoting any discounted price.",
        parameters=types.Schema(
            type="OBJECT",
            properties={},
        ),
    ),
    types.FunctionDeclaration(
        name="calculate_order_total",
        description="Calculate the final order total with correct pricing and applicable discounts. Always use this instead of doing math yourself.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "items": types.Schema(
                    type="ARRAY",
                    items=types.Schema(
                        type="OBJECT",
                        properties={
                            "product_id": types.Schema(type="STRING"),
                            "quantity": types.Schema(type="INTEGER"),
                        },
                    ),
                    description="List of items with product IDs and quantities",
                ),
                "customer_id": types.Schema(type="STRING"),
            },
            required=["items", "customer_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="create_order",
        description="Commit an order, decrement inventory, return order ID. ONLY call after customer has explicitly confirmed the final quoted total.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "customer_id": types.Schema(type="STRING"),
                "items": types.Schema(
                    type="ARRAY",
                    items=types.Schema(
                        type="OBJECT",
                        properties={
                            "product_id": types.Schema(type="STRING"),
                            "quantity": types.Schema(type="INTEGER"),
                            "unit_price": types.Schema(type="NUMBER"),
                        },
                    ),
                ),
                "total": types.Schema(type="NUMBER", description="Final total after discounts"),
                "notes": types.Schema(type="STRING", description="Any special instructions"),
            },
            required=["customer_id", "items", "total"],
        ),
    ),
    types.FunctionDeclaration(
        name="generate_invoice",
        description="Generate an invoice for a confirmed order. Returns formatted invoice text.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "order_id": types.Schema(type="STRING"),
            },
            required=["order_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="check_order_status",
        description="Look up order status by order ID or customer ID (returns most recent orders).",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "order_id": types.Schema(type="STRING"),
                "customer_id": types.Schema(type="STRING"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="escalate_to_owner",
        description="Hand off to the business owner. Creates escalation ticket, pauses conversation, notifies owner. Include a clear summary so the owner can act without re-reading the thread.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "reason": types.Schema(type="STRING", description="Why this is being escalated"),
                "conversation_summary": types.Schema(type="STRING", description="Concise summary of the conversation"),
                "suggested_action": types.Schema(type="STRING", description="What you recommend the owner do"),
            },
            required=["reason", "conversation_summary", "suggested_action"],
        ),
    ),
    types.FunctionDeclaration(
        name="log_action",
        description="Log an autonomous action to the audit trail. Call after every quote, discount application, order creation, or escalation. Mandatory bookkeeping.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "action": types.Schema(type="STRING", description="Action type (e.g. 'quote_given', 'order_created')"),
                "details": types.Schema(type="OBJECT", description="Structured details about the action"),
            },
            required=["action"],
        ),
    ),
]


def get_tool_config() -> types.Tool:
    """Return the Gemini Tool object with all function declarations."""
    return types.Tool(function_declarations=TOOL_DECLARATIONS)
