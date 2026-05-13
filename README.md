# Dr's Choice Chatbot — Backend

Stack: FastAPI + Anthropic Claude + Voyage AI (RAG) + Twilio WhatsApp  
Deploy: Railway (backend) + Vercel (frontend)

## Arquitectura

```
pdfs/                          ← Catálogos PDF del cliente (fuente de verdad)
urls.txt                       ← URLs de drchoice.cl a indexar
brandbook.json       ← Datos estáticos: empresa, brandbook, servicios
knowledge_base.json            ← Generado automáticamente ⚠️ no editar a mano
build_kb.py                    ← Script que genera el KB desde PDFs + URLs
main.py                        ← Backend FastAPI con RAG
knowledge_base.py              ← Prompt builder + utilidades RAG
.github/workflows/build_kb.yml ← Auto-actualización del KB en cada push
```

## Cómo actualizar el catálogo

### Agregar PDF nuevo
1. Subir PDF a la carpeta `pdfs/`
2. Hacer push → GitHub Actions regenera `knowledge_base.json` automáticamente

### Agregar URL nueva
1. Editar `urls.txt` y agregar la URL
2. Hacer push → regeneración automática

### Variables de entorno en Railway
- `ANTHROPIC_API_KEY`
- `VOYAGE_API_KEY`

## Arranque del servidor
Al arrancar, el servidor vectoriza el `knowledge_base.json` con Voyage AI (~15s la primera vez).
En cada mensaje de WhatsApp/web, Hermes recupera los 6 chunks más relevantes y José responde
con ese contexto — sin volcar los 292+ productos al prompt en cada llamada.
