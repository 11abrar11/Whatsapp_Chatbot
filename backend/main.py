"""
FastAPI Application Entry Point
Main application that receives webhook messages from the Baileys WhatsApp
service and processes them through the chatbot pipeline.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.webhook_handler import handle_baileys_webhook

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events."""
    logger.info("=" * 60)
    logger.info("PP5 WhatsApp Chatbot Backend — Starting")
    logger.info(f"  Groq Model:    {settings.groq_model}")
    logger.info(f"  Qdrant:        {settings.qdrant_host}:{settings.qdrant_port}")
    logger.info(f"  Collection:    {settings.qdrant_collection}")
    logger.info(f"  Baileys URL:   {settings.baileys_service_url}")
    logger.info(f"  Log Level:     {settings.log_level}")
    logger.info("=" * 60)
    yield
    logger.info("PP5 WhatsApp Chatbot Backend — Shutting down")


app = FastAPI(
    title="PP5 WhatsApp AI Chatbot",
    description="WhatsApp AI Lead Generation & FAQ Chatbot for PP5 Media Solutions",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "pp5-whatsapp-chatbot",
        "version": "1.0.0",
    }


@app.post("/webhook/baileys")
async def baileys_webhook(request: Request):
    """
    Receive incoming WhatsApp messages from the Baileys Node.js service.

    Baileys forwards JSON with:
    - phone: "+919999999999"
    - message: "Hello"
    - profile_name: "User's WhatsApp display name"

    Returns JSON response with processing result.
    """
    try:
        json_data = await request.json()

        logger.info(f"Received Baileys webhook: {json_data.get('phone', 'unknown')}")

        result = await handle_baileys_webhook(json_data)

        if result["status"] == "success":
            logger.info(f"Webhook processed successfully for {result.get('phone')}")
        else:
            logger.error(f"Webhook processing failed: {result.get('error')}")

        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        logger.error(f"Baileys webhook endpoint error: {e}")
        return JSONResponse(
            content={"status": "error", "error": str(e)},
            status_code=200,  # Return 200 to prevent retries
        )


@app.post("/webhook/n8n")
async def n8n_webhook(request: Request):
    """
    Alternative endpoint for n8n forwarding.
    n8n may forward the Baileys payload as JSON.
    """
    try:
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            json_data = await request.json()
            form_dict = json_data if isinstance(json_data, dict) else {}
        elif "form" in content_type:
            form_data = await request.form()
            form_dict = dict(form_data)
        else:
            try:
                json_data = await request.json()
                form_dict = json_data if isinstance(json_data, dict) else {}
            except Exception:
                form_data = await request.form()
                form_dict = dict(form_data)

        logger.info(f"Received n8n webhook: {form_dict.get('phone', 'unknown')}")

        result = await handle_baileys_webhook(form_dict)

        return JSONResponse(
            content=result,
            status_code=200,
        )

    except Exception as e:
        logger.error(f"n8n webhook endpoint error: {e}")
        return JSONResponse(
            content={"status": "error", "error": str(e)},
            status_code=200,
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=True,
        reload_dirs=["backend", "config", "prompts"]
    )
