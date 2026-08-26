# Dr's Choice Chatbot — Backend

Stack: FastAPI + Anthropic Claude + Voyage AI (RAG) + Twilio WhatsApp  
Deploy: Railway (backend) + Vercel (frontend)

## Arquitectura

```
pdfs/                          ← Catálogos PDF del cliente
data/                          ← Excels tabulares de productos
urls.txt                       ← URLs de drchoice.cl a indexar
brandbook.json                 ← Datos estáticos: empresa, brandbook, servicios
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

### Agregar Excel tabular de productos

1. Subir el Excel a `data/`
2. Idealmente nombrarlo `Drs Choice Tabular Completa.xlsx`
3. Hacer push → GitHub Actions regenera `knowledge_base.json`

### Agregar URL nueva
1. Editar `urls.txt` y agregar la URL
2. Hacer push → regeneración automática

### Variables de entorno en Railway
- `ANTHROPIC_API_KEY`
- `VOYAGE_API_KEY`

## Arranque del servidor
Al arrancar, el servidor vectoriza el `knowledge_base.json` con Voyage AI (~15s la primera vez).
En cada mensaje de WhatsApp/web, Hermes recupera los chunks más relevantes y José responde
con ese contexto — sin volcar los 292+ productos al prompt en cada llamada.


## Política comercial de José

José funciona como primer filtro comercial inteligente: atiende la consulta inicial, clasifica al cliente, registra datos clave y deriva al canal correcto.

Reglas vigentes:

- José no entrega precios, montos ni valores referenciales al usuario.
- José no confirma stock ni disponibilidad.
- Los precios o rangos internos solo se usan para calificar presupuesto, perfil y potencial del lead.
- Si el usuario es particular y el producto tiene URL de tienda online, José puede compartir el link y recordar que puede comprarlo en tienda.
- Si el usuario es profesional, institución, clínica, hospital, centro de rehabilitación o licitación, José no deriva a tienda online: captura datos y deriva a representante.
- Las oportunidades B2B se derivan internamente a `tzordan@doctorchoice.cl` para asignación de representante.
- Postventa, garantía, reparación o soporte técnico se deriva al formulario web `Soporte`.
- Imágenes o archivos adjuntos no se procesan por ahora; José pide un link o descripción breve.

Archivos de reglas:

- `commercial_policy.json`: política comercial editable sin tocar el código.
- `routing_rules.json`: matriz de intención/tipo de cliente/canal recomendado.
- `lead_router.py`: funciones de clasificación y routing comercial.
- `eval_cases.json`: casos de prueba para validar que José no entregue precios/stock y derive correctamente.
