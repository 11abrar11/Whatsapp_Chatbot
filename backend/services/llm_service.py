"""
LLM Service
Handles calling Groq (primary) for chat completions.
Parses and validates the structured JSON response from the LLM.
"""

import json
import logging
import re
from typing import Optional

from groq import Groq

from backend.config import get_settings
from backend.models import ChatbotResponse

logger = logging.getLogger(__name__)

# Singleton client
_groq_client: Optional[Groq] = None

MAX_RETRIES = 2


def _get_groq_client() -> Groq:
    """Get or create the Groq client."""
    global _groq_client
    if _groq_client is None:
        settings = get_settings()
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not set")
        _groq_client = Groq(api_key=settings.groq_api_key, max_retries=0)
        logger.info("Groq client initialized")
    return _groq_client


def _extract_json_from_text(text: str) -> Optional[dict]:
    """
    Try to extract valid JSON from LLM response text.
    Handles cases where the LLM wraps JSON in markdown code blocks.
    """
    # Try parsing directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON object pattern
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _validate_response(data: dict) -> ChatbotResponse:
    """
    Validate and parse the LLM response into a ChatbotResponse.
    Uses Pydantic for validation with defaults for missing fields.
    """
    return ChatbotResponse(**data)


async def generate_response(
    system_prompt: str,
    user_message: str,
) -> ChatbotResponse:
    """
    Generate a chatbot response using Groq LLM.
    
    Tries the primary model first. If it hits a 429 rate limit,
    automatically falls back to the secondary model which has
    separate rate limits on Groq.
    
    Args:
        system_prompt: The full system prompt (includes context, lead data, scoring rubric)
        user_message: The user's WhatsApp message
    
    Returns:
        Validated ChatbotResponse object
    
    Raises:
        ValueError: If valid JSON cannot be obtained after retries
    """
    settings = get_settings()
    client = _get_groq_client()

    # Models to try: primary first, then fallback
    models_to_try = [settings.groq_model, settings.groq_fallback_model]
    last_error = None

    for model in models_to_try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        rate_limited = False

        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(
                    f"Calling Groq ({model})"
                    f"{f' — retry {attempt}' if attempt > 0 else ''}"
                )

                completion = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.5,
                    max_tokens=1024,
                    response_format={"type": "json_object"},
                )

                raw_response = completion.choices[0].message.content
                logger.debug(f"Raw LLM response: {raw_response[:200]}...")

                # Parse JSON
                parsed = _extract_json_from_text(raw_response)
                if parsed is None:
                    raise ValueError(f"Could not extract JSON from response: {raw_response[:100]}")

                # Validate with Pydantic
                response = _validate_response(parsed)
                logger.info(
                    f"LLM response validated (model={model}) — "
                    f"escalation={response.escalation_required}"
                )
                return response

            except Exception as e:
                last_error = e
                error_str = str(e)

                # Check if it's a rate limit error (429)
                if "429" in error_str or "rate_limit" in error_str.lower():
                    logger.warning(
                        f"Rate limit hit on model {model}: {e}"
                    )
                    rate_limited = True
                    break  # Don't retry same model, switch to fallback

                logger.warning(f"LLM attempt {attempt + 1}/{MAX_RETRIES + 1} failed ({model}): {e}")

                if attempt < MAX_RETRIES:
                    # Add a hint to the messages for retry
                    messages.append({
                        "role": "assistant",
                        "content": raw_response if "raw_response" in dir() else "",
                    })
                    messages.append({
                        "role": "user",
                        "content": (
                            "Your previous response was not valid JSON. "
                            "Please respond with ONLY a valid JSON object matching the required schema. "
                            "Do not include any text outside the JSON object."
                        ),
                    })

        if rate_limited and model != models_to_try[-1]:
            logger.info(f"Switching to fallback model: {models_to_try[-1]}")
            continue  # Try next model
        elif not rate_limited:
            break  # Non-rate-limit error, don't try fallback

    # All retries exhausted — return a safe fallback response
    logger.error(f"All LLM attempts failed. Last error: {last_error}")
    return ChatbotResponse(
        reply=(
            "Oops! I'm having a little bit of trouble connecting right now. 😅 "
            "Could you please try sending your message again in a moment? "
            "If it's urgent, you can also reach our team directly at "
            "support@pp5mediasolutions.com or WhatsApp +91 99593 94534."
        ),
        lead_update={},
        missing_information=[],
        conversation_stage="New",
        summary="LLM response error — fallback message sent",
        escalation_required=False,
    )
