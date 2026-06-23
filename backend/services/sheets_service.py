"""
Google Sheets Service
Handles lead lookup, creation, and updates in Google Sheets.
Phone number is the primary key (Column A).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from backend.config import get_settings
from backend.models import LeadData

logger = logging.getLogger(__name__)

# Google Sheets API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Column headers matching the master prompt specification
SHEET_HEADERS = [
    "Phone",
    "Name",
    "Business",
    "Industry",
    "Requirement",
    "Monthly Leads",
    "Company Size",
    "Budget",
    "Timeline",
    "Decision Maker",
    "Lead Score",
    "Lead Status",
    "Conversation Stage",
    "Missing Information",
    "Summary",
    "Escalated",
    "Last Updated",
]

# Singleton client
_sheets_client = None
_worksheet = None


def _get_worksheet():
    """Get or create the Google Sheets worksheet connection."""
    global _sheets_client, _worksheet

    if _worksheet is not None:
        return _worksheet

    settings = get_settings()

    try:
        creds = Credentials.from_service_account_file(
            settings.google_service_account_json,
            scopes=SCOPES,
        )
        _sheets_client = gspread.authorize(creds)
        spreadsheet = _sheets_client.open_by_key(settings.google_sheet_id)
        _worksheet = spreadsheet.sheet1

        # Ensure headers exist
        existing_headers = _worksheet.row_values(1)
        if not existing_headers:
            _worksheet.update("A1", [SHEET_HEADERS])
            logger.info("Created sheet headers")

        logger.info(f"Connected to Google Sheet: {spreadsheet.title}")
        return _worksheet
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        raise


def lookup_lead(phone: str) -> Optional[LeadData]:
    """
    Look up a lead by phone number in the Google Sheet.
    
    Args:
        phone: Phone number to search for (e.g., +919999999999)
    
    Returns:
        LeadData if found, None if not found
    """
    try:
        worksheet = _get_worksheet()
        # In gspread 6.x, find() returns None if not found (no exception)
        cell = worksheet.find(phone, in_column=1)

        if cell is None:
            logger.info(f"Lead not found: {phone}")
            return None

        # Get the entire row
        row_values = worksheet.row_values(cell.row)

        # Pad row to ensure we have all columns
        while len(row_values) < len(SHEET_HEADERS):
            row_values.append("")

        lead = LeadData(
            phone=row_values[0],
            name=row_values[1] or None,
            business=row_values[2] or None,
            industry=row_values[3] or None,
            requirement=row_values[4] or None,
            monthly_leads=row_values[5] or None,
            company_size=row_values[6] or None,
            budget=row_values[7] or None,
            timeline=row_values[8] or None,
            decision_maker=row_values[9] or None,
            lead_score=int(row_values[10]) if row_values[10] else 0,
            lead_status=row_values[11] or "Cold",
            conversation_stage=row_values[12] or "New",
            missing_information=row_values[13] or "",
            summary=row_values[14] or "",
            escalated=row_values[15] or "FALSE",
            last_updated=row_values[16] or "",
        )

        logger.info(f"Lead found: {phone} (status: {lead.lead_status})")
        return lead

    except Exception as e:
        logger.error(f"Error looking up lead {phone}: {e}")
        return None


def update_or_create_lead(phone: str, lead_update: dict, chatbot_response) -> bool:
    """
    Update an existing lead row or create a new one.
    
    Args:
        phone: Phone number (primary key)
        lead_update: Dict of field values to update from LLM response
        chatbot_response: The full ChatbotResponse object
    
    Returns:
        True if successful, False otherwise
    """
    try:
        worksheet = _get_worksheet()
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        timestamp = datetime.now(ist_tz).strftime("%Y-%m-%d %H:%M:%S IST")

        # Determine the correct lead_status (must always be score-based, never "Escalated")
        lead_status = chatbot_response.lead_status
        if lead_status == "Escalated":
            # LLM incorrectly set status to "Escalated" — fall back to score-based classification
            score = chatbot_response.lead_score
            if score >= 70:
                lead_status = "Hot"
            elif score >= 40:
                lead_status = "Warm"
            else:
                lead_status = "Cold"

        # Build the row data
        row_data = {
            "Phone": phone,
            "Name": lead_update.get("name", ""),
            "Business": lead_update.get("business", ""),
            "Industry": lead_update.get("industry", ""),
            "Requirement": lead_update.get("requirement", ""),
            "Monthly Leads": lead_update.get("monthly_leads", ""),
            "Company Size": lead_update.get("company_size", ""),
            "Budget": lead_update.get("budget", ""),
            "Timeline": lead_update.get("timeline", ""),
            "Decision Maker": lead_update.get("decision_maker", ""),
            "Lead Score": str(chatbot_response.lead_score),
            "Lead Status": lead_status,
            "Conversation Stage": chatbot_response.conversation_stage,
            "Missing Information": ", ".join(chatbot_response.missing_information),
            "Summary": chatbot_response.summary,
            "Escalated": "TRUE" if chatbot_response.escalation_required else "FALSE",
            "Last Updated": timestamp,
        }

        # Check if lead exists (find() returns None in gspread 6.x)
        cell = worksheet.find(phone, in_column=1)

        if cell is not None:
            # Lead exists — merge with existing data
            existing_row = cell.row
            existing_values = worksheet.row_values(existing_row)
            while len(existing_values) < len(SHEET_HEADERS):
                existing_values.append("")

            # Only overwrite non-empty new values
            for i, header in enumerate(SHEET_HEADERS):
                new_value = row_data.get(header, "")
                if not new_value and i < len(existing_values):
                    row_data[header] = existing_values[i]

            # Update the existing row
            row_list = [row_data.get(h, "") for h in SHEET_HEADERS]
            worksheet.update(
                f"A{existing_row}:{_col_letter(len(SHEET_HEADERS))}{existing_row}",
                [row_list],
            )
            logger.info(f"Updated lead row {existing_row} for {phone}")
        else:
            # Create new row
            row_list = [row_data.get(h, "") for h in SHEET_HEADERS]
            worksheet.append_row(row_list)
            logger.info(f"Created new lead row for {phone}")

        return True

    except Exception as e:
        logger.error(f"Failed to update/create lead for {phone}: {e}")
        return False


def _col_letter(col_num: int) -> str:
    """Convert a column number (1-indexed) to a letter (A, B, ..., Z, AA, ...)."""
    result = ""
    while col_num > 0:
        col_num -= 1
        result = chr(65 + col_num % 26) + result
        col_num //= 26
    return result
