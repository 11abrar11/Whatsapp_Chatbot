# Sample Test Conversations

Use these scripts to verify the chatbot is working correctly after deployment.

---

## Test 1: New Lead + FAQ Question

**Goal**: Verify the bot answers from knowledge base AND asks one qualifying question.

| # | Who | Message | Expected Behavior |
|---|-----|---------|-------------------|
| 1 | User | "Hi, do you build websites?" | Bot answers YES (from services.md) + asks ONE qualifying question (e.g., business type) |
| 2 | User | "I run a restaurant chain in Bangalore" | Bot acknowledges business + asks about requirement or another missing field |
| 3 | User | "We need a new website and brand identity" | Bot confirms they can help + asks about timeline or budget |
| 4 | User | "Within the next month" | Bot notes urgency + asks about budget or company size |

**Verify in Google Sheets:**
- New row created with phone number
- Name populated (from WhatsApp profile)
- Business: "Restaurant chain"
- Requirement: "Website and brand identity"
- Timeline: "Within the next month"
- Lead Score: Should increase progressively
- Lead Status: Should be "Warm" or "Hot" depending on info provided
- Conversation Stage: Should progress from "New" → "Discovering" → "Qualifying"

---

## Test 2: Returning User (Context Memory)

**Goal**: Verify the bot remembers previous conversation context.

**Prerequisite**: Complete Test 1 first from the same phone number.

| # | Who | Message | Expected Behavior |
|---|-----|---------|-------------------|
| 1 | User | "Hi, I'm back. Can you tell me about your design services?" | Bot answers from KB + references their previous conversation (e.g., "Welcome back!") |
| 2 | User | "Yes, we also need logo design" | Bot does NOT re-ask business or timeline (already known) + asks about remaining missing fields |

**Verify in Google Sheets:**
- Same row updated (not a new row)
- Requirement updated to include logo design
- Missing Information list should be shorter
- Summary updated with new context

---

## Test 3: Financial Escalation

**Goal**: Verify pricing/discount questions trigger escalation.

| # | Who | Message | Expected Behavior |
|---|-----|---------|-------------------|
| 1 | User | "What are your pricing packages?" | Bot responds with standard escalation message: "Thank you for reaching out regarding this. Our team has been notified and will connect with you shortly." |
| 2 | (Check email) | — | Escalation email received with lead details |

**Variations to test** (each should trigger escalation):
- "Can I get a discount?"
- "Please send me a quotation"
- "What's the cost for a logo design?"
- "I need a refund"
- "Can you send me an invoice?"
- "Let's discuss the contract terms"

**Verify in Google Sheets:**
- Escalated: TRUE
- Lead Status: "Escalated"
- Conversation Stage: "Escalated"

**Verify Gmail:**
- Email received at `ESCALATION_RECIPIENT`
- Subject: "Financial Query Escalation"
- Body contains: phone, message, lead score, lead status, summary

---

## Test 4: Not-Interested / Out-of-Scope

**Goal**: Verify the bot handles non-relevant questions gracefully.

| # | Who | Message | Expected Behavior |
|---|-----|---------|-------------------|
| 1 | User | "What's the weather like today?" | Bot says it doesn't have that information + provides contact details + tries to redirect to PP5 services |
| 2 | User | "Do you sell mobile phones?" | Bot says it doesn't have that information + briefly mentions what PP5 actually does |
| 3 | User | "I'm not interested anymore" | Bot responds gracefully + marks as not interested |

**Verify in Google Sheets:**
- Lead Status: "Not Interested" (after message 3)
- Conversation Stage: "Closed"

---

## Test 5: Full Qualification Flow (End-to-End)

**Goal**: Fill all qualification fields across multiple messages.

| # | Who | Message | Expected Behavior |
|---|-----|---------|-------------------|
| 1 | User | "Hello, what services do you offer?" | Bot answers from KB + asks about business |
| 2 | User | "I'm the marketing director at TechCorp, we're a SaaS company with about 200 employees" | Bot extracts: business=TechCorp, industry=SaaS, company_size=200, decision_maker=marketing director |
| 3 | User | "We need social media content and animated banners for our campaigns" | Bot answers relevance from KB + asks about volume/timeline |
| 4 | User | "About 50 pieces per month, we need to start next quarter" | Bot extracts: monthly_leads=50/month, timeline=next quarter |
| 5 | User | "Our budget for this is around $5000 per month" | Bot extracts: budget=$5000/month |

**Verify in Google Sheets:**
- All fields populated
- Lead Score: 70+ (should be Warm or Hot)
- Lead Status: "Qualified" or "Hot"
- Conversation Stage: "Qualified"
- Missing Information: should be empty or minimal
- Summary: comprehensive overview of the lead

---

## Common Issues During Testing

| Issue | Possible Cause | Fix |
|-------|---------------|-----|
| Bot doesn't respond | Backend error | Check: `docker compose logs -f backend` |
| "I don't have information" on FAQ | Knowledge base not ingested | Re-run: `docker compose --profile ingestion run --rm ingestion` |
| Sheets not updating | Service account permissions | Re-share sheet with service account email |
| Escalation email missing | Gmail credentials wrong | Test App Password in `.env` |
| Bot asks already-answered questions | Sheet lookup failing | Check backend logs for Sheets errors |
