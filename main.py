"""
Dr's Choice WhatsApp Chatbot Backend
Stack: FastAPI + Twilio + Anthropic
Deploy: Railway / Render (gratis para MVP)
"""
import os, json, httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from knowledge_base import load_kb, build_system_prompt

app = FastAPI(title="Dr's Choice Chatbot")

# ─── CONFIG ──────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL             = "claude-sonnet-4-20250514"
MAX_TOKENS        = 800

# Carga KB una vez al iniciar
KB            = load_kb()
SYSTEM_PROMPT = build_system_prompt(KB)

# Historial en memoria por número de teléfono
# En producción usar Redis o DB
conversation_store: dict[str, list] = {}

# ─── HELPERS ────────────────────────────────────────────
async def call_claude(messages: list) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM_PROMPT,
                "messages": messages,
            },
        )
        data = resp.json()
        return data["content"][0]["text"]

def get_history(phone: str) -> list:
    if phone not in conversation_store:
        conversation_store[phone] = []
    return conversation_store[phone]

def trim_history(history: list, max_turns: int = 10) -> list:
    """Mantiene los últimos N turnos para no exceder contexto."""
    if len(history) > max_turns * 2:
        return history[-(max_turns * 2):]
    return history

# ─── RUTAS ──────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "bot": "Dr's Choice Chatbot", "version": "1.0.0"}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
):
    """
    Recibe mensajes entrantes de Twilio WhatsApp Sandbox.
    Twilio envía: From (número), Body (texto del usuario)
    """
    phone   = From.replace("whatsapp:", "")
    user_msg = Body.strip()

    if not user_msg:
        return PlainTextResponse(str(MessagingResponse()), media_type="text/xml")

    # Recuperar historial
    history = get_history(phone)
    history.append({"role": "user", "content": user_msg})
    history = trim_history(history)

    # Llamar a Claude
    try:
        reply = await call_claude(history)
    except Exception as e:
        reply = (
            "Lo siento, tuve un problema técnico. "
            "Por favor contáctanos directamente al +56 9 6159 8525 💬"
        )

    # Guardar respuesta en historial
    history.append({"role": "assistant", "content": reply})
    conversation_store[phone] = history

    # Responder a Twilio
    twiml = MessagingResponse()
    twiml.message(reply)
    return PlainTextResponse(str(twiml), media_type="text/xml")

@app.delete("/conversation/{phone}")
def clear_conversation(phone: str):
    """Limpia historial de un número (útil para testing)."""
    if phone in conversation_store:
        del conversation_store[phone]
    return {"cleared": phone}

@app.get("/conversations")
def list_conversations():
    """Debug: lista conversaciones activas."""
    return {
        phone: len(msgs) // 2
        for phone, msgs in conversation_store.items()
    }
