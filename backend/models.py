"""
Pydantic Data Models
Defines the structured data types used throughout the application.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ChatbotResponse(BaseModel):
    """
    The structured JSON response that the LLM must return.
    Matches the exact schema from the master prompt.
    """
    reply: str = Field(
        description="The WhatsApp reply message to send to the user"
    )
    lead_update: dict = Field(
        default_factory=dict,
        description="Key-value pairs of lead fields to update",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="List of lead fields still missing",
    )
    conversation_stage: Literal[
        "New", "Discovering", "Qualifying", "Qualified", "Escalated", "Closed"
    ] = Field(
        default="New",
        description="Current stage of the conversation",
    )
    summary: str = Field(
        default="",
        description="Brief summary of the lead and conversation so far",
    )
    escalation_required: bool = Field(
        default=False,
        description="Whether this message requires human escalation",
    )


class LeadData(BaseModel):
    """
    Represents a lead row in the Google Sheet.
    Phone is the primary key.
    """
    phone: str
    name: Optional[str] = None
    business: Optional[str] = None
    industry: Optional[str] = None
    requirement: Optional[str] = None
    monthly_leads: Optional[str] = None
    company_size: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    decision_maker: Optional[str] = None
    lead_score: int = 0
    lead_status: str = "Cold"
    conversation_stage: str = "New"
    missing_information: str = ""
    summary: str = ""
    escalated: str = "FALSE"
    last_updated: str = ""


class IncomingMessage(BaseModel):
    """Parsed incoming WhatsApp message from Baileys."""
    phone: str
    message: str
    profile_name: Optional[str] = None
