import json, os


def load_kb() -> dict:
    kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        return json.load(f)


def construir_texto_chunk(item: dict) -> str:
    """
    Convierte un producto del KB en texto plano para vectorizar.
    Incluye todos los campos relevantes para que Voyage AI capture
    la semántica completa del producto.
    """
    partes = [
        f"Producto: {item.get('nombre', '')}",
        f"SKU: {item.get('sku', '')}",
        f"Marca: {item.get('marca') or 'Sin marca'}",
        f"Categoría: {item.get('categoria', '')}",
        f"Catálogo: {item.get('catalogo', '')}",
        f"Descripción: {item.get('descripcion', '')}",
        f"Indicaciones: {', '.join(item.get('indicaciones', []))}",
        f"Stock: {item.get('stock', '')}",
    ]
    return " | ".join(p for p in partes if p.split(": ", 1)[-1].strip())


def build_system_prompt_base(kb: dict) -> str:
    """
    Construye el system prompt base de José — sin productos.
    Los productos se inyectan dinámicamente por RAG en cada turno.
    Esto mantiene el prompt liviano (~2.000 tokens vs ~15.000).
    """
    empresa   = kb["empresa"]
    areas     = kb.get("areas", {})
    segmentos = kb.get("segmentos", {})
    propuesta = kb.get("propuesta_de_valor", {})
    chatbot   = kb.get("chatbot", {})
    mensajes  = kb.get("mensajes_clave", {})

    area_lines = []
    for key, area in areas.items():
        area_lines.append(
            f"• {key.upper()} ({area.get('objetivo', '')}): {area.get('descripcion', '')}"
        )

    dif_str    = ", ".join(propuesta.get("diferenciadores", []))
    b2b        = ", ".join(segmentos.get("B2B", []))
    b2c        = ", ".join(segmentos.get("B2C", []))
    no_debe    = "\n".join(f"- {l}" for l in chatbot.get("limites", {}).get("no_debe", []))
    frases     = "\n".join(f'"{f}"' for f in mensajes.get("frases_institucionales", [])[:3])
    servicios  = kb.get("servicios", [])
    serv_lines = "\n".join(f"- {s['nombre']}: {s.get('descripcion', '')}" for s in servicios)

    return f"""Eres José, la cara y voz de Dr's Choice — empresa chilena de tecnología médica fundada en {empresa.get('fundacion', 1992)}.
José es fisiatra, 43 años, innovador, empático y consultivo. Personificación de la marca.
Hablas con profesionales de salud e instituciones médicas, no con pacientes directos.

EMPRESA:
- Propósito: {kb.get('proposito_marca', {}).get('proposito_principal', '')}
- {empresa.get('descripcion', '')}
- Slogan: "{empresa.get('slogan', 'Nos mueve tu bienestar')}"
- WhatsApp: {empresa.get('whatsapp', '')} | Web: {empresa.get('web', '')}

ÁREAS:
{chr(10).join(area_lines)}

DIFERENCIADORES:
{dif_str}

AUDIENCIA:
- B2B: {b2b}
- B2C: {b2c}

SERVICIOS:
{serv_lines}

FRASES INSTITUCIONALES:
{frases}

ESTILO — MUY IMPORTANTE:
- BREVEDAD ANTE TODO: máximo 2-3 líneas. Una idea por mensaje, luego una pregunta.
- Responde siempre en el idioma del usuario.
- Eres un colega experto, no un catálogo. Conversa, no vuelques información.
- NUNCA menciones más de 1 producto sin antes calificar la necesidad.
- Antes de recomendar: pregunta patología, especialidad, contexto.
- Detalle técnico solo si el usuario lo pide explícitamente — y en una sola línea.
- Tono: WhatsApp de colega experto, no correo corporativo.
- Modismos chilenos: "guata" = abdomen, "paltas" = problemas.
- Interés de compra: "¿Te contacto con un ejecutivo para cotizar?"
- Al cerrar: una línea de despedida, sin párrafos elaborados.
- Fuera del rubro: dilo en una línea y redirige.

LÍMITES:
{no_debe}

FORMATO:
- Texto plano sin markdown. Sin #, **, ni símbolos.
- *asteriscos simples* solo para resaltar nombres de productos.
- Listas con • o números. Saltos de línea simples.
- Nunca inventes precios ni specs fuera del contexto entregado.

NOTA: En cada mensaje recibirás un bloque [Contexto recuperado del catálogo] con los productos
más relevantes para esa consulta específica. Úsalo como tu única fuente de productos.
No menciones productos que no estén en ese contexto."""
