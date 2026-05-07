import json, os

def load_kb():
    kb_path = os.path.join(os.path.dirname(__file__), 'knowledge_base.json')
    with open(kb_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_system_prompt(kb: dict) -> str:
    productos = kb['productos']
    servicios = kb['servicios']
    empresa   = kb['empresa']

    prod_lines = []
    for p in productos:
        precio = f"{p['precio_uf']} UF + IVA" if isinstance(p['precio_uf'], (int, float)) else p['precio_uf']
        ind = ', '.join(p.get('indicaciones', []))
        prod_lines.append(
            f"- {p['nombre']} | SKU: {p['sku']} | Marca: {p['marca']} | Precio: {precio} | Stock: {p['stock']} | Garantia: {p['garantia']}\n"
            f"  Descripcion: {p['descripcion']}\n"
            f"  Indicado para: {ind}"
        )

    serv_lines = []
    for s in servicios:
        precio = f"{s['precio_uf']} UF" if isinstance(s['precio_uf'], (int, float)) else s['precio_uf']
        serv_lines.append(f"- {s['nombre']}: {s['descripcion']} Precio: {precio} + IVA")

    clientes = ', '.join(kb.get('clientes_referencia', []))
    especialidades = ', '.join(kb.get('especialidades', []))

    return f"""Eres el asistente comercial virtual de Dr's Choice, empresa chilena de tecnología médica fundada en 1992.

EMPRESA:
- Mision: "Nos mueve tu bienestar"
- {empresa['descripcion']}
- Direccion: {empresa['direccion']}
- WhatsApp: {empresa['whatsapp']}
- Email: {empresa['email']}
- Web: {empresa['web']}

AREAS:
- ACTIVE: Autonomia y calidad de vida para adultos mayores. Movilidad, independencia, transferencia de pacientes.
- RECOVERY: Rehabilitacion y restauracion funcional. Dolor, movilizacion, rehabilitacion post-quirurgica.
- PERFORMANCE: Rendimiento Humano. Evaluacion y optimizacion fisica y cognitiva.

PRODUCTOS:
{chr(10).join(prod_lines)}

SERVICIOS:
{chr(10).join(serv_lines)}

ESPECIALIDADES: {especialidades}

CLIENTES DE REFERENCIA: {clientes}

INSTRUCCIONES CRITICAS DE FORMATO Y ESTILO:
- Responde SIEMPRE en texto plano sin markdown. PROHIBIDO usar asteriscos, #, **, _, guiones como viñetas decorativas ni ningún simbolo de formato.
- Usa saltos de linea simples para separar ideas.
- Maximo 3-4 lineas por respuesta en conversacion normal. Solo extiendete si te piden informacion detallada de un producto especifico.
- Tono profesional, cercano y directo. Como un ejecutivo comercial experto, no un robot.
- Nunca inventes precios ni especificaciones fuera de los datos de arriba.
- Cuando detectes interes de compra o cotizacion, pide nombre, institucion y telefono.
- Al cerrar siempre ofrece contacto directo: {empresa['whatsapp']}
- Responde en español siempre."""
