# Dr's Choice Chatbot — Backend MVP

## Stack
- **FastAPI** — servidor web
- **Anthropic Claude** — motor de IA
- **Twilio** — canal WhatsApp
- **Railway/Render** — deploy gratuito

## Setup local (5 minutos)

```bash
pip install -r requirements.txt
cp .env.example .env
# Edita .env con tu ANTHROPIC_API_KEY
uvicorn main:app --reload
```

## Deploy en Railway (recomendado para MVP)

1. Crea cuenta en https://railway.app
2. "New Project" → "Deploy from GitHub" (sube este repo)
3. En Variables de entorno añade: ANTHROPIC_API_KEY=sk-ant-...
4. Railway te da una URL pública automáticamente: https://tu-app.railway.app

## Configurar Twilio WhatsApp Sandbox

1. Crea cuenta en https://twilio.com (gratis)
2. Ve a Messaging → Try it out → Send a WhatsApp message
3. Sigue las instrucciones para activar el sandbox en tu celular
4. En "Sandbox Settings" → When a message comes in:
   → Pega tu URL: https://tu-app.railway.app/webhook/whatsapp
   → Método: POST
5. Listo — cualquier mensaje al sandbox llega al bot

## Para el KOM (demo en vivo)
- Thomas escribe al número sandbox de Twilio
- El bot responde con datos reales de productos y precios
- Funciona desde cualquier celular con WhatsApp

## Pasar a producción (post-KOM)
- Solicitar número WhatsApp Business real a Twilio (~$1 USD/mes)
- Migrar historial de conversaciones a Redis o PostgreSQL
- Reemplazar knowledge_base.json con datos reales de Thomas
