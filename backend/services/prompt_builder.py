"""
Prompt Builder Service
Assembles the complete prompt for the LLM from system prompt template,
retrieved RAG context, existing lead data, and the user's message.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from backend.models import LeadData

logger = logging.getLogger(__name__)

# Cache loaded prompts
_system_prompt_cache: Optional[str] = None
_scoring_prompt_cache: Optional[str] = None


def _load_prompt_file(filename: str) -> str:
    """Load a prompt file from the prompts/ directory."""
    # Check multiple locations
    search_paths = [
        Path(__file__).parent.parent.parent / "prompts" / filename,  # project root
        Path("/app/prompts") / filename,  # Docker
    ]

    for path in search_paths:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            logger.info(f"Loaded prompt: {path}")
            return content

    raise FileNotFoundError(
        f"Prompt file '{filename}' not found. Searched: {search_paths}"
    )


def get_system_prompt() -> str:
    """Load and cache the system prompt."""
    global _system_prompt_cache
    if _system_prompt_cache is None:
        _system_prompt_cache = _load_prompt_file("system_prompt.txt")
    return _system_prompt_cache


def get_scoring_prompt() -> str:
    """Load and cache the lead scoring prompt."""
    global _scoring_prompt_cache
    if _scoring_prompt_cache is None:
        _scoring_prompt_cache = _load_prompt_file("lead_scoring_prompt.txt")
    return _scoring_prompt_cache


def _format_context_chunks(chunks: list[dict]) -> str:
    """Format retrieved RAG chunks into a readable context block."""
    if not chunks:
        return "No relevant context found in the knowledge base."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("filename", "unknown")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")
        context_parts.append(
            f"[Source {i}: {source} (relevance: {score})]\n{text}"
        )

    return "\n\n".join(context_parts)


def _format_lead_data(lead: Optional[LeadData]) -> str:
    """Format existing lead data for the prompt."""
    if lead is None:
        return "This is a NEW lead. No previous interaction data available."

    parts = [
        "EXISTING LEAD DATA (from previous interactions):",
        f"  Phone: {lead.phone}",
    ]

    field_map = {
        "Name": lead.name,
        "Business": lead.business,
        "Industry": lead.industry,
        "Requirement": lead.requirement,
        "Monthly Leads": lead.monthly_leads,
        "Company Size": lead.company_size,
        "Budget": lead.budget,
        "Timeline": lead.timeline,
        "Decision Maker": lead.decision_maker,
        "Lead Score": lead.lead_score,
        "Lead Status": lead.lead_status,
        "Conversation Stage": lead.conversation_stage,
    }

    for field_name, value in field_map.items():
        if value:
            parts.append(f"  {field_name}: {value}")

    if lead.summary:
        parts.append(f"\n  Previous Summary: {lead.summary}")

    if lead.missing_information:
        parts.append(f"\n  Still Missing: {lead.missing_information}")

    return "\n".join(parts)


def _compute_missing_fields(lead: Optional[LeadData]) -> list[str]:
    """Determine which lead qualification fields are still missing.
    
    Note: 'industry' is NOT tracked here because it is auto-inferred
    from the business field by the LLM (see system prompt rule #8).
    
    Budget values like 'Not Disclosed' are treated as filled — the bot
    should not re-ask once the client has declined to share.
    """
    tracked_fields = {
        "business": "business",
        "requirement": "requirement",
        "budget": "budget",
        "timeline": "timeline",
        "decision_maker": "decision_maker",
        "company_size": "company_size",
        "monthly_leads": "monthly_leads",
    }

    if lead is None:
        return list(tracked_fields.keys())

    missing = []
    for field_key, attr_name in tracked_fields.items():
        value = getattr(lead, attr_name, None)
        if not value:
            missing.append(field_key)
        elif field_key == "budget" and value.strip().lower() == "not disclosed":
            # Budget was refused — treat as filled, do NOT re-ask
            pass

    return missing


def build_prompt(
    context_chunks: list[dict],
    lead_data: Optional[LeadData],
    user_message: str,
    conversation_history: str = "",
) -> str:
    """
    Build the complete system prompt for the LLM.
    
    Combines:
    1. Base system prompt (role, rules, behavior)
    2. Lead scoring rubric
    3. Retrieved knowledge base context
    4. Existing lead data (for returning users)
    5. Conversation history (for continuity)
    6. Missing information list
    7. Required JSON output schema
    
    Args:
        context_chunks: RAG results from Qdrant search
        lead_data: Existing lead data from Google Sheets (or None for new leads)
        user_message: The current user message (included for context)
        conversation_history: Formatted conversation history text
    
    Returns:
        Complete system prompt string
    """
    system_prompt = get_system_prompt()
    scoring_prompt = get_scoring_prompt()
    context_text = _format_context_chunks(context_chunks)
    lead_text = _format_lead_data(lead_data)
    missing_fields = _compute_missing_fields(lead_data)

    # Build conversation history section
    history_section = ""
    if conversation_history and conversation_history != "No previous messages in this conversation.":
        history_section = f"""
---

{conversation_history}

IMPORTANT: Use the conversation history above to maintain context. Do NOT repeat questions the user has already answered. Do NOT re-ask for information already provided. Build on the conversation naturally.
"""

    # Assemble the complete prompt
    full_prompt = f"""{system_prompt}

---

{scoring_prompt}

---

RETRIEVED KNOWLEDGE BASE CONTEXT:
{context_text}

---

{lead_text}
{history_section}
---

MISSING QUALIFICATION FIELDS (ask about ONE of these naturally, AFTER answering the user's question):
{json.dumps(missing_fields)}

---

REQUIRED JSON OUTPUT FORMAT:
You MUST respond with ONLY a valid JSON object. No text before or after.
{{
  "reply": "Your WhatsApp response message to the user",
  "lead_update": {{"field_name": "value"}},
  "missing_information": ["field1", "field2"],
  "lead_score": 0,
  "lead_status": "Cold",
  "conversation_stage": "New",
  "summary": "Updated summary of this lead",
  "escalation_required": false
}}

Valid lead_status values: Cold, Warm, Hot, Qualified, Not Interested
Valid conversation_stage values: New, Discovering, Qualifying, Qualified, Escalated, Closed
"""

    logger.debug(f"Built prompt ({len(full_prompt)} chars)")
    return full_prompt
