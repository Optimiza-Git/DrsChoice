"""
Dr's Choice WhatsApp + Web Chatbot Backend
Stack: FastAPI + Anthropic
Deploy: Railway
"""
import os, httpx
from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from knowledge_base import load_kb, build_system_prompt

app = FastAPI(title="Dr's Choice Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-3-5-haiku-20241022"
MAX_TOKENS = 800

KB = load_kb()
SYSTEM_PROMPT = build_system_prompt(KB)

conversation_store: dict[str, list] = {}

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
        print(f"ANTHROPIC RESPONSE: {data}")
        if "content" not in data:
            return f"API Error: {data.get('error', {}).get('message', str(data))}"
        return data["content"][0]["text"]

@app.get("/")
def health():
    return {"status": "ok", "bot": "Dr's Choice Chatbot", "version": "1.0.0"}

class ChatRequest(BaseModel):
    messages: list

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        reply = await call_claude(request.messages)
        return {"reply": reply}
    except Exception as e:
            print(f"ERROR ANTHROPIC: {str(e)}")
            return {"reply": f"Error: {str(e)}"}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...)):
    from twilio.twiml.messaging_response import MessagingResponse
    phone = From.replace("whatsapp:", "")
    user_msg = Body.strip()
    if not user_msg:
        return PlainTextResponse(str(MessagingResponse()), media_type="text/xml")
    history = conversation_store.get(phone, [])
    history.append({"role": "user", "content": user_msg})
    if len(history) > 20:
        history = history[-20:]
    try:
        reply = await call_claude(history)
    except:
        reply = "Lo siento, tuve un problema. Escríbenos al +56 9 6159 8525 💬"
    history.append({"role": "assistant", "content": reply})
    conversation_store[phone] = history
    twiml = MessagingResponse()
    twiml.message(reply)
    return PlainTextResponse(str(twiml), media_type="text/xml")
