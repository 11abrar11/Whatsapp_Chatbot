"""
Webhook Handler
Main orchestration logic — ties all services together.
Handles the complete flow from incoming message to response.
"""

import logging
import traceback

from backend.models import IncomingMessage
from backend.services import (
    baileys_service,
    sheets_service,
    rag_service,
    llm_service,
    gmail_service,
    prompt_builder,
)
from backend.services.memory_service import get_conversation_store

logger = logging.getLogger(__name__)


async def handle_baileys_webhook(json_data: dict) -> dict:
    """
    Process an incoming WhatsApp message through the complete pipeline.

    Flow:
    1. Parse incoming Baileys message
    2. Look up existing lead in Google Sheets
    3. Search knowledge base via Qdrant
    4. Get conversation history
    5. Build prompt and call LLM
    6. Save conversation to memory
    7. Update Google Sheet with lead data
    8. Send WhatsApp reply via Baileys
    9. Send escalation email if required

    Args:
        json_data: Dict from Baileys Node.js service POST

    Returns:
        Dict with status and details for logging
    """
    incoming = None

    try:
        # === Step 1: Parse incoming message ===
        logger.info("=" * 50)
        logger.info("STEP 1: Parsing incoming message")
        incoming = baileys_service.parse_incoming_message(json_data)
        logger.info(
            f"From: {incoming.phone}, "
            f"Name: {incoming.profile_name}, "
            f"Message: {incoming.message[:80]}..."
        )

        # === Step 2: Look up existing lead ===
        logger.info("STEP 2: Looking up lead in Google Sheets")
        lead_data = None
        try:
            lead_data = sheets_service.lookup_lead(incoming.phone)
            if lead_data:
                logger.info(
                    f"Returning lead — Status: {lead_data.lead_status}, "
                    f"Stage: {lead_data.conversation_stage}"
                )
            else:
                logger.info("New lead — no previous data")
        except Exception as e:
            logger.error(f"Sheets lookup failed (continuing without lead data): {e}")

        # === Step 3: Search knowledge base ===
        logger.info("STEP 3: Searching knowledge base")
        context_chunks = []
        try:
            context_chunks = rag_service.search_knowledge(incoming.message)
            logger.info(f"Retrieved {len(context_chunks)} context chunks")
        except Exception as e:
            logger.error(f"RAG search failed (continuing without context): {e}")

        # === Step 4: Get conversation history ===
        logger.info("STEP 4: Getting conversation history")
        memory = get_conversation_store()
        conversation_history = memory.get_history_as_text(incoming.phone)
        history_count = len(memory.get_history(incoming.phone))
        logger.info(f"Conversation history: {history_count} previous messages")

        # Store the user's current message in memory
        memory.add_message(incoming.phone, "user", incoming.message)

        # === Step 5: Build prompt and call LLM ===
        logger.info("STEP 5: Generating LLM response")
        full_prompt = prompt_builder.build_prompt(
            context_chunks=context_chunks,
            lead_data=lead_data,
            user_message=incoming.message,
            conversation_history=conversation_history,
        )

        chatbot_response = await llm_service.generate_response(
            system_prompt=full_prompt,
            user_message=incoming.message,
        )
        logger.info(
            f"LLM response — Reply: {chatbot_response.reply[:60]}..., "
            f"Escalation: {chatbot_response.escalation_required}"
        )

        # === Step 6: Store bot's reply in memory ===
        memory.add_message(incoming.phone, "assistant", chatbot_response.reply)

        # === Step 7: Update Google Sheet ===
        logger.info("STEP 7: Updating Google Sheet")
        final_score = 0
        final_status = "Cold"
        try:
            # Merge profile name into lead_update if available
            lead_update = chatbot_response.lead_update.copy()
            if incoming.profile_name and not lead_update.get("name"):
                lead_update["name"] = incoming.profile_name

            final_score, final_status = sheets_service.update_or_create_lead(
                phone=incoming.phone,
                lead_update=lead_update,
                chatbot_response=chatbot_response,
            )
            logger.info("Google Sheet updated successfully")
        except Exception as e:
            logger.error(f"Sheets update failed (continuing with reply): {e}")

        # === Step 8: Send WhatsApp reply via Baileys ===
        logger.info("STEP 8: Sending WhatsApp reply via Baileys")
        try:
            await baileys_service.send_whatsapp_reply(
                to_phone=incoming.phone,
                body=chatbot_response.reply,
            )
            logger.info("WhatsApp reply sent successfully")
        except Exception as e:
            logger.error(f"Failed to send WhatsApp reply: {e}")
            raise  # This is critical — re-raise

        # === Step 9: Handle escalation ===
        if chatbot_response.escalation_required:
            logger.info("STEP 9: Sending escalation email")
            try:
                await gmail_service.send_escalation_email(
                    phone=incoming.phone,
                    user_message=incoming.message,
                    lead_score=final_score,
                    lead_status=final_status,
                    summary=chatbot_response.summary,
                )
                logger.info("Escalation email sent")
            except Exception as e:
                logger.error(f"Escalation email failed (non-critical): {e}")
        else:
            logger.info("STEP 9: No escalation required — skipping")

        logger.info("=" * 50)
        logger.info("WEBHOOK PROCESSING COMPLETE")

        return {
            "status": "success",
            "phone": incoming.phone,
            "lead_score": final_score,
            "lead_status": final_status,
            "escalated": chatbot_response.escalation_required,
        }

    except Exception as e:
        logger.error(f"Webhook handler error: {e}")
        logger.error(traceback.format_exc())

        # Try to send an error reply to the user via Baileys
        if incoming:
            try:
                await baileys_service.send_whatsapp_reply(
                    to_phone=incoming.phone,
                    body=(
                        "Oops! I'm having a little bit of trouble connecting right now. 😅 "
                        "Could you please try sending your message again in a moment? "
                        "If it's urgent, you can also reach our team directly at "
                        "support@pp5mediasolutions.com or WhatsApp +91 99593 94534."
                    ),
                )
            except Exception:
                logger.error("Failed to send error reply to user")

        return {
            "status": "error",
            "error": str(e),
        }
