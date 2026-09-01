"""
Agent Engine — The brain of the WhatsApp Commerce Platform.
Manages the full Gemini tool-calling loop with:
- Gap #5: Per-conversation advisory locking
- Gap #3: Escalation resume path
- Gap #6: Token/cost tracking
- Graceful degradation on API failures
"""

import json
import logging
from datetime import datetime, timezone

from google import genai
from google.genai import types

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Seller, Conversation
from app.agent.system_prompt import system_prompt_builder
from app.agent.context_builder import context_builder
from app.agent.tools.registry import get_tool_config
from app.agent.tools.inventory import search_inventory
from app.agent.tools.customer import get_customer_history
from app.agent.tools.pricing import get_discount_policy, calculate_order_total
from app.agent.tools.orders import create_order, check_order_status
from app.agent.tools.invoice import generate_invoice
from app.agent.tools.escalation import escalate_to_owner
from app.agent.tools.logging_tool import log_action
from app.services.conversation_service import conversation_service
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)
settings = get_settings()

# Cost estimates per 1M tokens (Gemini 2.0 Flash approximate pricing)
COST_PER_1M_INPUT_TOKENS = 0.10  # USD
COST_PER_1M_OUTPUT_TOKENS = 0.40  # USD
USD_TO_INR = 85.0


class AgentEngine:
    """
    The agentic loop. One invocation per incoming message.
    Calls Gemini with tool definitions, executes tool calls,
    feeds results back, loops until a final text response or escalation.
    """

    MAX_ITERATIONS = 10

    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def process_message(
        self,
        db: AsyncSession,
        customer_id: str,
        conversation_id: str,
        seller: Seller,
        incoming_message: str,
    ) -> str:
        """
        Process a customer message through the full agentic loop.
        Returns the agent's final text response.
        """
        # Gap #5: Acquire per-conversation lock
        await conversation_service.acquire_lock(db, conversation_id)

        # Build context
        context = await context_builder.build(
            db=db,
            conversation_id=conversation_id,
            customer_id=customer_id,
        )

        # Check if conversation is paused (awaiting escalation)
        if context.is_paused:
            return await self._handle_paused_conversation(
                db, seller.id, conversation_id, context, incoming_message
            )

        # Assemble system prompt
        system_prompt = system_prompt_builder.build(
            business_name=seller.business_name,
            product_category=seller.product_category,
            auto_approve_limit=seller.auto_approve_order_limit,
            customer_id=customer_id,
            seller_id=seller.id,
            customer_context=context.customer_summary,
        )

        # Build message history for Gemini
        contents = self._build_contents(context.recent_messages, incoming_message)

        # Run the agentic loop
        return await self._run_loop(
            db=db,
            system_prompt=system_prompt,
            contents=contents,
            seller_id=seller.id,
            customer_id=customer_id,
            conversation_id=conversation_id,
        )

    async def resume_from_escalation(
        self,
        db: AsyncSession,
        conversation_id: str,
        seller: Seller,
        customer_id: str,
        seller_instruction: str,
    ) -> str:
        """
        Gap #3: Resume a paused conversation after seller resolves escalation.
        Called by the dashboard API when seller provides an instruction.
        """
        # Acquire lock
        await conversation_service.acquire_lock(db, conversation_id)

        # Build context
        context = await context_builder.build(
            db=db,
            conversation_id=conversation_id,
            customer_id=customer_id,
        )

        # Build system prompt WITH seller instruction
        system_prompt = system_prompt_builder.build(
            business_name=seller.business_name,
            product_category=seller.product_category,
            auto_approve_limit=seller.auto_approve_order_limit,
            customer_id=customer_id,
            seller_id=seller.id,
            customer_context=context.customer_summary,
            seller_instruction=seller_instruction,
        )

        # Build contents — include a synthetic message about the instruction
        contents = self._build_contents(context.recent_messages)
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(
                    f"[SYSTEM: The owner has reviewed the escalation and provided this instruction: {seller_instruction}. Follow the owner's instruction to respond to the customer.]"
                )],
            )
        )

        # Unpause the conversation
        await conversation_service.unpause(db, conversation_id)

        # Run the loop
        return await self._run_loop(
            db=db,
            system_prompt=system_prompt,
            contents=contents,
            seller_id=seller.id,
            customer_id=customer_id,
            conversation_id=conversation_id,
        )

    async def _run_loop(
        self,
        db: AsyncSession,
        system_prompt: str,
        contents: list,
        seller_id: str,
        customer_id: str,
        conversation_id: str,
    ) -> str:
        """The core Gemini tool-calling loop."""
        total_tokens_used = 0
        all_tool_calls = []
        iteration = 0

        while iteration < self.MAX_ITERATIONS:
            iteration += 1

            try:
                response = self.client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        tools=[get_tool_config()],
                        temperature=0.7,
                    ),
                )
            except Exception as e:
                logger.error(f"Gemini API error: {e}", exc_info=True)
                # Graceful degradation — auto-escalate
                try:
                    await escalate_to_owner(
                        db=db,
                        seller_id=seller_id,
                        customer_id=customer_id,
                        conversation_id=conversation_id,
                        reason=f"Gemini API failure: {type(e).__name__}",
                        conversation_summary="Agent could not process — API error",
                        suggested_action="Manual response needed",
                    )
                except Exception:
                    pass
                return "Let me check on this and get back to you shortly 🙏"

            # Track token usage (Gap #6)
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                input_tokens = getattr(usage, 'prompt_token_count', 0) or 0
                output_tokens = getattr(usage, 'candidates_token_count', 0) or 0
                total_tokens_used += input_tokens + output_tokens

            # Check if response has function calls
            candidate = response.candidates[0] if response.candidates else None
            if not candidate or not candidate.content or not candidate.content.parts:
                return "Let me check on this and get back to you shortly 🙏"

            parts = candidate.content.parts
            function_calls = [p for p in parts if p.function_call]
            text_parts = [p for p in parts if p.text]

            if function_calls:
                # Execute tool calls
                contents.append(candidate.content)

                tool_response_parts = []
                for fc_part in function_calls:
                    fc = fc_part.function_call
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}

                    logger.info(f"Tool call [{iteration}]: {tool_name}({json.dumps(tool_args, default=str)[:200]})")

                    # Execute the tool
                    result = await self._execute_tool(
                        db=db,
                        tool_name=tool_name,
                        args=tool_args,
                        seller_id=seller_id,
                        customer_id=customer_id,
                        conversation_id=conversation_id,
                    )

                    all_tool_calls.append({
                        "iteration": iteration,
                        "tool": tool_name,
                        "args": tool_args,
                        "result_preview": str(result)[:500],
                    })

                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response=result if isinstance(result, dict) else {"result": str(result)},
                        )
                    )

                contents.append(
                    types.Content(role="user", parts=tool_response_parts)
                )
                continue  # Loop back for next Gemini decision

            # Final text response
            if text_parts:
                final_text = " ".join(p.text for p in text_parts if p.text)

                # Log cost
                if total_tokens_used > 0:
                    cost_usd = (total_tokens_used / 1_000_000) * (COST_PER_1M_INPUT_TOKENS + COST_PER_1M_OUTPUT_TOKENS) / 2
                    cost_inr = cost_usd * USD_TO_INR
                    await log_action(
                        db=db,
                        seller_id=seller_id,
                        conversation_id=conversation_id,
                        action="conversation_turn",
                        details={
                            "iterations": iteration,
                            "tool_calls": len(all_tool_calls),
                            "tools_used": [tc["tool"] for tc in all_tool_calls],
                        },
                        tokens_used=total_tokens_used,
                        estimated_cost_inr=round(cost_inr, 4),
                    )

                return final_text

        # Safety: max iterations exceeded
        logger.warning(f"Agent exceeded MAX_ITERATIONS for conversation {conversation_id}")
        try:
            await escalate_to_owner(
                db=db,
                seller_id=seller_id,
                customer_id=customer_id,
                conversation_id=conversation_id,
                reason="Agent exceeded maximum reasoning steps",
                conversation_summary="Agent may be stuck in a loop",
                suggested_action="Review conversation — manual response likely needed",
            )
        except Exception:
            pass
        return "Let me check with the owner on this one, I'll get back to you shortly 🙏"

    async def _execute_tool(
        self,
        db: AsyncSession,
        tool_name: str,
        args: dict,
        seller_id: str,
        customer_id: str,
        conversation_id: str,
    ) -> dict:
        """Dispatch a tool call to the correct implementation."""
        try:
            match tool_name:
                case "search_inventory":
                    return await search_inventory(
                        db=db,
                        seller_id=seller_id,
                        query=args.get("query", ""),
                        filters=args.get("filters"),
                    )
                case "get_customer_history":
                    return await get_customer_history(
                        db=db,
                        customer_id=args.get("customer_id", customer_id),
                    )
                case "get_discount_policy":
                    return await get_discount_policy(db=db, seller_id=seller_id)
                case "calculate_order_total":
                    return await calculate_order_total(
                        db=db,
                        seller_id=seller_id,
                        items=args.get("items", []),
                        customer_id=args.get("customer_id", customer_id),
                    )
                case "create_order":
                    return await create_order(
                        db=db,
                        seller_id=seller_id,
                        customer_id=args.get("customer_id", customer_id),
                        conversation_id=conversation_id,
                        items=args.get("items", []),
                        total=args.get("total", 0),
                        notes=args.get("notes"),
                    )
                case "generate_invoice":
                    return await generate_invoice(
                        db=db,
                        order_id=args.get("order_id", ""),
                    )
                case "check_order_status":
                    return await check_order_status(
                        db=db,
                        order_id=args.get("order_id"),
                        customer_id=args.get("customer_id"),
                    )
                case "escalate_to_owner":
                    return await escalate_to_owner(
                        db=db,
                        seller_id=seller_id,
                        customer_id=customer_id,
                        conversation_id=conversation_id,
                        reason=args.get("reason", "Unknown"),
                        conversation_summary=args.get("conversation_summary", ""),
                        suggested_action=args.get("suggested_action", ""),
                    )
                case "log_action":
                    return await log_action(
                        db=db,
                        seller_id=seller_id,
                        conversation_id=conversation_id,
                        action=args.get("action", "unknown"),
                        details=args.get("details"),
                    )
                case _:
                    return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool execution error [{tool_name}]: {e}", exc_info=True)
            return {
                "error": f"Tool '{tool_name}' failed: {str(e)}",
                "instruction": "Inform the customer you're having a technical issue and escalate if this is a critical operation.",
            }

    async def _handle_paused_conversation(
        self,
        db: AsyncSession,
        seller_id: str,
        conversation_id: str,
        context,
        new_message: str,
    ) -> str:
        """Handle messages received while conversation is paused for escalation."""
        # Notify seller of follow-up
        if context.active_escalation:
            await notification_service.push_escalation_followup(
                seller_id=seller_id,
                escalation_id=context.active_escalation["escalation_id"],
                message=new_message,
            )

        return "I'm still waiting to hear back from the owner on your request — I'll update you as soon as I have an answer 🙏"

    def _build_contents(
        self, messages: list, new_message: str | None = None
    ) -> list[types.Content]:
        """Convert DB messages to Gemini Content objects."""
        contents = []
        for msg in messages:
            role = "user" if msg.sender == "customer" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(msg.content)],
                )
            )

        if new_message:
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(new_message)],
                )
            )

        return contents


# Singleton
agent_engine = AgentEngine()
