# BUILD THIS PROJECT - WHATSAPP AI LEAD GENERATION & FAQ CHATBOT

## Objective

Build a production-ready MVP WhatsApp chatbot that:

* Answers company questions using RAG.
* Qualifies leads naturally.
* Stores lead information in Google Sheets.
* Maintains lead memory.
* Tracks missing lead information.
* Generates lead scores.
* Creates lead summaries.
* Escalates financial discussions via Gmail.
* Uses Baileys for WhatsApp messaging.
* Uses Qdrant for RAG retrieval.

The system should be deployable within 1-2 days and designed for future scalability.

---

# Architecture

```text
Knowledge Base Files
(company_overview.md
services.md
faqs.md
pricing_guidelines.md
case_studies.md
contact_information.md)

        ↓

Document Loader

        ↓

Chunking

        ↓

OpenAI Embeddings

        ↓

Qdrant Vector Database

==================================================

Customer

        ↓

WhatsApp

        ↓

        ↓

FastAPI Webhook

        ↓

Load Existing Lead From Google Sheet

        ↓

Retrieve Relevant Context From Qdrant

        ↓

GPT

        ↓

Structured JSON Response

        ↓

Update Google Sheet

        ↓

Send WhatsApp Response via Baileys

        ↓

If Escalation = TRUE

        ↓

Send Gmail To Team
```

---

# Required Technologies

Frontend:

* WhatsApp

Messaging Layer:

* Baileys (WhatsApp Web Library)

Workflow Layer:

* FastAPI Background Tasks

LLM:

* OpenAI GPT

Embeddings:

* OpenAI Embeddings

Vector Database:

* Qdrant

Storage:

* Google Sheets

Escalation:

* Gmail

Deployment:

* Docker
* Docker Compose

---

# Folder Structure

```text
project/

├── knowledge_base/
│   ├── company_overview.md
│   ├── services.md
│   ├── faqs.md
│   ├── pricing_guidelines.md
│   ├── case_studies.md
│   └── contact_information.md
│
├── ingestion/
│   ├── chunk_documents.py
│   ├── embed_documents.py
│   └── upload_to_qdrant.py
│
├── prompts/
│   ├── system_prompt.txt
│   └── lead_scoring_prompt.txt
│
├── baileys/
│   └── index.js
│
├── config/
│   └── .env.example
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
└── README.md
```

---

# Knowledge Base System

Build an ingestion pipeline.

Requirements:

1. Read every file in /knowledge_base
2. Chunk documents
3. Generate embeddings
4. Store vectors in Qdrant
5. Attach metadata:

   * filename
   * chunk_id
   * document_type

At query time:

1. Embed user question
2. Search Qdrant
3. Retrieve top 5 chunks
4. Send chunks to GPT

The chatbot must answer only from retrieved context.

Do not hallucinate company information.

---

# Lead Memory System

Google Sheet is the source of truth.

One row per phone number.

Phone number is the primary key.

If phone exists:

Update row.

If phone does not exist:

Create row.

---

# Google Sheet Columns

Phone

Name

Business

Industry

Requirement

Monthly Leads

Company Size

Budget

Timeline

Decision Maker

Lead Score

Lead Status

Conversation Stage

Missing Information

Summary

Escalated

Last Updated

---

# Lead Status

Possible values:

Cold

Warm

Hot

Qualified

Escalated

Not Interested

---

# Conversation Stage

Possible values:

New

Discovering

Qualifying

Qualified

Escalated

Closed

---

# Missing Information Logic

Track:

Business

Requirement

Budget

Timeline

Decision Maker

Company Size

Monthly Leads

Example:

```json
{
  "missing_information": [
    "budget",
    "timeline",
    "decision_maker"
  ]
}
```

The chatbot should only ask questions related to missing information.

---

# Qualification Rules

Very Important

The chatbot must:

* Answer the user's question first.
* Ask at most one qualification question.
* Never ask multiple questions together.
* Never sound like a form.
* Never sound robotic.

Bad:

"What is your business?
What is your budget?
What is your timeline?"

Good:

"We do provide WhatsApp chatbot solutions. May I ask what type of business you're running?"

---

# FAQ Behavior

Example:

User:

Do you build WhatsApp chatbots?

Bot:

Yes, we build WhatsApp chatbot solutions for businesses. May I ask what kind of business you're operating?

FAQ answered.

Lead qualification progressed.

---

# Returning Users

When a user returns:

Load:

* Existing row
* Existing summary
* Existing missing information

Pass this context to GPT.

Do not ask questions already answered.

---

# Lead Scoring

Generate score:

0-100

Consider:

* Business fit
* Requirement clarity
* Budget
* Timeline
* Decision maker status
* Company size
* Monthly leads

Classification:

80-100 = Hot

50-79 = Warm

0-49 = Cold

---

# Financial Escalation

Immediately escalate:

Pricing negotiation

Discount requests

Quotation requests

Refund requests

Invoices

Payment issues

Contracts

Legal matters

Commercial discussions

If detected:

1. escalation_required = true
2. Update Google Sheet
3. Send Gmail
4. Reply:

"Thank you for contacting us. Our team has been notified and will connect with you shortly."

No human takeover required.

---

# Gmail Format

Subject:

Financial Query Escalation

Body:

Phone Number

Latest User Message

Lead Score

Lead Status

Summary

Timestamp

---

# GPT Output Format

The LLM must always return valid JSON.

```json
{
  "reply": "",
  "lead_update": {},
  "missing_information": [],
  "lead_score": 0,
  "lead_status": "",
  "conversation_stage": "",
  "summary": "",
  "escalation_required": false
}
```

Validate all outputs.

Retry on invalid JSON.

---

# System Prompt Requirements

The assistant must:

* Be professional.
* Be concise.
* Be helpful.
* Never hallucinate.
* Never invent pricing.
* Never negotiate.
* Never promise delivery dates.
* Never ask more than one qualification question.
* Use retrieved context only.
* Help first.
* Qualify second.

---



# Deliverables

Generate:

1. Full project structure.
2. Docker configuration.
3. Qdrant setup.
4. Embedding pipeline.
5. Knowledge ingestion pipeline.
6. Baileys integration.
7. Google Sheet integration.
8. Gmail integration.
9. Gmail integration.
10. System prompt.
11. Environment variables.
12. Setup guide.
13. Deployment guide.
14. Sample test conversations.
15. Error handling and logging.

The final result should be a fully functioning WhatsApp lead generation and FAQ chatbot that can be deployed immediately after API keys and company documents are added.
