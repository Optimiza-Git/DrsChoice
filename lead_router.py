"""Reglas comerciales y routing para José · Dr's Choice.

Este módulo evita que la política comercial quede mezclada en el prompt principal.
La lógica es intencionalmente simple y auditable: reglas por palabras clave + señales
provenientes del clasificador LLM.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def cargar_json(path: str | Path, default: dict | None = None) -> dict:
    path = Path(path)
    if not path.exists():
        return default or {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalizar(texto: str) -> str:
    texto = (texto or "").lower()
    reemplazos = str.maketrans("áéíóúüñ", "aeiouun")
    return texto.translate(reemplazos)


POSTVENTA_KW = [
    "postventa", "post venta", "garantia", "garantía", "falla", "fallo",
    "reclamo", "reparacion", "reparación", "servicio tecnico", "servicio técnico",
    "soporte", "seguimiento", "devolucion", "devolución", "cambio", "no funciona"
]

LICITACION_KW = [
    "licitacion", "licitación", "concurso", "bases", "propuesta", "adjudicacion",
    "adjudicación", "mercado publico", "mercado público", "compra publica", "compra pública"
]

INSTITUCION_KW = [
    "clinica", "clínica", "hospital", "cesfam", "centro medico", "centro médico",
    "centro de rehabilitacion", "centro de rehabilitación", "institucion", "institución",
    "universidad", "fundacion", "fundación", "mutual", "red de salud"
]

PROFESIONAL_KW = [
    "kinesiologo", "kinesiólogo", "kinesiologa", "kinesióloga", "terapeuta",
    "fisiatra", "traumatologo", "traumatólogo", "doctor", "doctora", "dr.", "dra.",
    "medico", "médico", "profesional", "consulta", "pacientes", "rehabilitacion", "rehabilitación"
]

PARTICULAR_KW = [
    "soy paciente", "mi mama", "mi mamá", "mi papa", "mi papá", "mi hijo", "mi hija",
    "para mi", "para mí", "para uso personal", "particular", "comprar online", "tienda online"
]

COTIZACION_KW = [
    "cotizar", "cotizacion", "cotización", "precio", "valor", "cuanto", "cuánto",
    "presupuesto", "disponibilidad", "stock", "comprar", "compra", "necesito", "me interesa"
]

COMPRA_RAPIDA_KW = ["comprar online", "tienda online", "link", "comprar ahora", "pagar", "carrito"]

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?56\s?)?(?:9\s?)?\d{4}\s?\d{4}")


def inferir_tipo_cliente(mensaje: str, clasificador: dict | None = None, historial: list | None = None) -> str:
    texto = normalizar(" ".join([
        mensaje or "",
        " ".join(str(m.get("content", "")) for m in (historial or [])[-6:]),
        json.dumps((clasificador or {}).get("datos", {}), ensure_ascii=False)
    ]))

    if any(normalizar(k) in texto for k in POSTVENTA_KW):
        return "postventa"
    if any(normalizar(k) in texto for k in LICITACION_KW):
        return "licitacion"
    if any(normalizar(k) in texto for k in INSTITUCION_KW):
        return "institucion"
    if any(normalizar(k) in texto for k in PARTICULAR_KW):
        return "particular"
    if any(normalizar(k) in texto for k in PROFESIONAL_KW):
        return "profesional_salud"

    segmento = (clasificador or {}).get("segmento", "")
    score = float((clasificador or {}).get("score_final", (clasificador or {}).get("score", 50)) or 50)
    if segmento in {"profesional", "medico", "especialista"} or score >= 61:
        return "profesional_salud"

    return "desconocido"


def inferir_intencion(mensaje: str, tipo_cliente: str) -> str:
    texto = normalizar(mensaje or "")
    if tipo_cliente == "postventa" or any(normalizar(k) in texto for k in POSTVENTA_KW):
        return "postventa"
    if tipo_cliente == "licitacion" or any(normalizar(k) in texto for k in LICITACION_KW):
        return "licitacion"
    if any(normalizar(k) in texto for k in COMPRA_RAPIDA_KW):
        return "compra_rapida"
    if any(normalizar(k) in texto for k in COTIZACION_KW):
        return "cotizacion" if tipo_cliente in {"profesional_salud", "institucion", "licitacion"} else "compra_producto"
    return "consulta_producto"


def contexto_tiene_tienda_online(contexto_catalogo: str) -> bool:
    texto = contexto_catalogo or ""
    return "URL tienda online:" in texto or "tienda.doctorchoice.cl" in texto


def extraer_datos_contacto(historial: list | None, mensaje: str) -> dict[str, Any]:
    texto = "\n".join([str(m.get("content", "")) for m in (historial or [])] + [mensaje or ""])
    email = EMAIL_RE.search(texto)
    phone = PHONE_RE.search(texto)
    return {
        "email": email.group(0) if email else None,
        "telefono": phone.group(0) if phone else None,
    }


def resolver_derivacion(
    mensaje: str,
    clasificador: dict | None,
    historial: list | None,
    contexto_catalogo: str,
    commercial_policy: dict,
    routing_rules: dict,
) -> dict[str, Any]:
    tipo_cliente = inferir_tipo_cliente(mensaje, clasificador, historial)
    intencion = inferir_intencion(mensaje, tipo_cliente)
    tiene_tienda = contexto_tiene_tienda_online(contexto_catalogo)
    contacto = extraer_datos_contacto(historial, mensaje)

    destino_ventas = commercial_policy.get("cotizacion_b2b", {}).get("derivar_a", "tzordan@doctorchoice.cl")
    soporte_url = commercial_policy.get("postventa", {}).get("url", "https://drchoice.cl/soporte/")

    canal = "nurturing"
    accion = "hacer_una_pregunta_de_calificacion"
    destino = None
    permite_tienda = False

    if tipo_cliente == "postventa" or intencion == "postventa":
        canal = "postventa"
        accion = "derivar_formulario_soporte"
        destino = soporte_url
    elif tipo_cliente in {"institucion", "licitacion", "profesional_salud"} or intencion == "licitacion":
        canal = "ventas_b2b"
        accion = "capturar_contacto_y_derivar_tzordan"
        destino = destino_ventas
    elif tipo_cliente == "particular" and tiene_tienda:
        canal = "tienda_online"
        accion = "enviar_link_tienda_y_recordar_compra_online"
        destino = "url_tienda_online_del_producto"
        permite_tienda = True
    elif tipo_cliente == "particular":
        canal = "ventas_b2b"
        accion = "capturar_contacto_y_derivar_tzordan"
        destino = destino_ventas
    elif intencion in {"cotizacion", "compra_producto", "compra_rapida"}:
        canal = "ventas_b2b"
        accion = "capturar_contacto_y_derivar_tzordan"
        destino = destino_ventas

    datos_faltantes = []
    if not contacto.get("telefono") and not contacto.get("email"):
        datos_faltantes.append("telefono_o_email")
    if tipo_cliente in {"institucion", "licitacion", "profesional_salud"}:
        datos_faltantes.extend(["nombre", "institucion_o_rol"])
    else:
        datos_faltantes.append("nombre")

    es_lead_potencial = canal in {"ventas_b2b", "tienda_online", "postventa"}

    return {
        "tipo_cliente": tipo_cliente,
        "intencion": intencion,
        "canal_recomendado": canal,
        "accion": accion,
        "destino_derivacion": destino,
        "permite_tienda_online": permite_tienda,
        "producto_con_tienda_online": tiene_tienda,
        "datos_contacto_detectados": contacto,
        "datos_faltantes": list(dict.fromkeys(datos_faltantes)),
        "es_lead_potencial": es_lead_potencial,
    }


def construir_bloque_routing(routing: dict | None) -> str:
    if not routing:
        return "Sin routing calculado. Califica la necesidad antes de derivar."
    return "\n".join([
        f"- Tipo cliente probable: {routing.get('tipo_cliente')}",
        f"- Intención probable: {routing.get('intencion')}",
        f"- Canal recomendado: {routing.get('canal_recomendado')}",
        f"- Acción comercial: {routing.get('accion')}",
        f"- Destino interno: {routing.get('destino_derivacion')}",
        f"- Producto con tienda online: {routing.get('producto_con_tienda_online')}",
        f"- Datos faltantes: {', '.join(routing.get('datos_faltantes', []))}",
    ])
