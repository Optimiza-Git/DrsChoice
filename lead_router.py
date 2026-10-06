"""Reglas comerciales y routing para José · Dr's Choice.

La lógica determinística resuelve intenciones críticas (postventa, reembolso,
B2B/B2C) y valida contacto antes de confirmar un lead.
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


REEMBOLSO_COBERTURA_KW = [
    "reembolso isapre", "isapre", "seguro complementario", "codigo de reembolso",
    "código de reembolso", "reembolsable", "bonificacion", "bonificación",
    "cobertura de reembolso", "cobertura seguro", "institucion beneficiadora",
    "institución beneficiadora", "fonasa"
]
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

EMAIL_RE = re.compile(r"(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![A-Z0-9._%+-])", re.IGNORECASE)
EMAIL_CANDIDATE_RE = re.compile(r"(?:correo|email|e-mail|mail)\s*(?:es|:|=)?\s*([^\s,;]+)", re.IGNORECASE)
PHONE_CANDIDATE_RE = re.compile(r"(?:telefono|teléfono|celular|fono|whatsapp)\s*(?:es|:|=)?\s*([+\d][\d\s().-]{6,30})", re.IGNORECASE)
PHONE_GENERIC_RE = re.compile(r"(?<!\d)(?:\+?56[\s().-]*)?(?:\d[\s().-]*){9}(?!\d)")


def validar_email(valor: str | None) -> bool:
    return bool(valor and EMAIL_RE.fullmatch(valor.strip()))


def normalizar_telefono(valor: str | None) -> str | None:
    if not valor:
        return None
    digits = re.sub(r"\D", "", valor)
    if len(digits) == 11 and digits.startswith("56"):
        digits = digits[2:]
    return digits


def validar_telefono_chile(valor: str | None) -> bool:
    digits = normalizar_telefono(valor)
    return bool(digits and len(digits) == 9)


def _texto_historial(historial: list | None, mensaje: str) -> str:
    return "\n".join([str(m.get("content", "")) for m in (historial or [])] + [mensaje or ""])


def extraer_datos_contacto(historial: list | None, mensaje: str, phone_origen: str | None = None) -> dict[str, Any]:
    texto = _texto_historial(historial, mensaje)
    email_match = EMAIL_RE.search(texto)
    phone_match = PHONE_GENERIC_RE.search(texto)

    ultimo = mensaje or ""
    email_cand_match = EMAIL_CANDIDATE_RE.search(ultimo)
    phone_cand_match = PHONE_CANDIDATE_RE.search(ultimo)
    email_candidato = email_cand_match.group(1).strip(" .") if email_cand_match else None
    telefono_candidato = phone_cand_match.group(1).strip() if phone_cand_match else None

    email_valido = email_match.group(0) if email_match else None
    telefono_valido = phone_match.group(0) if phone_match and validar_telefono_chile(phone_match.group(0)) else None

    # El número de origen de WhatsApp es un contacto válido aunque el usuario no lo escriba.
    telefono_origen = None
    if phone_origen and phone_origen != "web_user" and validar_telefono_chile(phone_origen):
        telefono_origen = phone_origen

    errores = []
    if email_candidato and not validar_email(email_candidato):
        errores.append("email_invalido")
    if telefono_candidato and not validar_telefono_chile(telefono_candidato):
        errores.append("telefono_invalido")

    return {
        "email": email_valido,
        "telefono": telefono_valido or telefono_origen,
        "telefono_origen_whatsapp": telefono_origen,
        "email_candidato": email_candidato,
        "telefono_candidato": telefono_candidato,
        "errores_validacion": errores,
        "contacto_valido": bool(email_valido or telefono_valido or telefono_origen),
    }


def es_consulta_reembolso_cobertura(mensaje: str, historial: list | None = None) -> bool:
    # Se decide por el mensaje actual para que una consulta previa de Isapre no
    # contamine todos los turnos siguientes de la misma conversación.
    texto = normalizar(mensaje or "")
    return any(normalizar(k) in texto for k in REEMBOLSO_COBERTURA_KW)


def inferir_tipo_cliente(mensaje: str, clasificador: dict | None = None, historial: list | None = None) -> str:
    texto = normalizar(" ".join([
        mensaje or "",
        " ".join(str(m.get("content", "")) for m in (historial or [])[-6:]),
        json.dumps((clasificador or {}).get("datos", {}), ensure_ascii=False)
    ]))
    # Reembolso Isapre/seguro es información administrativa, no postventa técnica.
    if not es_consulta_reembolso_cobertura(mensaje, historial) and any(normalizar(k) in texto for k in POSTVENTA_KW):
        return "postventa"
    if any(normalizar(k) in texto for k in LICITACION_KW):
        return "licitacion"
    if any(normalizar(k) in texto for k in INSTITUCION_KW):
        return "institucion"
    if any(normalizar(k) in texto for k in PARTICULAR_KW):
        return "particular"
    if any(normalizar(k) in texto for k in PROFESIONAL_KW):
        return "profesional_salud"
    tipo_clf = (clasificador or {}).get("tipo_cliente")
    if tipo_clf in {"particular", "profesional_salud", "institucion", "licitacion", "postventa"}:
        return tipo_clf
    segmento = (clasificador or {}).get("segmento", "")
    score = float((clasificador or {}).get("score_final", (clasificador or {}).get("score", 50)) or 50)
    if segmento in {"profesional", "medico", "especialista"} or score >= 61:
        return "profesional_salud"
    return "desconocido"


def inferir_intencion(mensaje: str, tipo_cliente: str, historial: list | None = None) -> str:
    texto = normalizar(mensaje or "")
    if es_consulta_reembolso_cobertura(mensaje, historial):
        return "reembolso_cobertura"
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
    return "URL tienda online:" in texto or "tienda.doctorchoice.cl" in texto or "tienda.drchoice.cl" in texto


def resolver_derivacion(mensaje: str, clasificador: dict | None, historial: list | None,
                       contexto_catalogo: str, commercial_policy: dict, routing_rules: dict,
                       phone_origen: str | None = None) -> dict[str, Any]:
    tipo_cliente = inferir_tipo_cliente(mensaje, clasificador, historial)
    intencion = inferir_intencion(mensaje, tipo_cliente, historial)
    tiene_tienda = contexto_tiene_tienda_online(contexto_catalogo)
    contacto = extraer_datos_contacto(historial, mensaje, phone_origen)
    destino_ventas = commercial_policy.get("cotizacion_b2b", {}).get("derivar_a", "tzordan@doctorchoice.cl")
    soporte_url = commercial_policy.get("postventa", {}).get("url", "")

    canal, accion, destino, permite_tienda = "nurturing", "hacer_una_pregunta_de_calificacion", None, False
    if intencion == "reembolso_cobertura":
        canal, accion = "informacion_reembolso", "responder_politica_reembolso"
    elif tipo_cliente == "postventa" or intencion == "postventa":
        canal, accion, destino = "postventa", "derivar_formulario_soporte", soporte_url
    elif tipo_cliente in {"institucion", "licitacion", "profesional_salud"} or intencion == "licitacion":
        canal, accion, destino = "ventas_b2b", "capturar_contacto_y_derivar_tzordan", destino_ventas
    elif tipo_cliente == "particular" and tiene_tienda:
        canal, accion, destino, permite_tienda = "tienda_online", "enviar_link_tienda_y_recordar_compra_online", "url_tienda_online_del_producto", True
    elif tipo_cliente == "particular":
        canal, accion, destino = "ventas_b2b", "capturar_contacto_y_derivar_tzordan", destino_ventas
    elif intencion in {"cotizacion", "compra_producto", "compra_rapida"}:
        canal, accion, destino = "ventas_b2b", "capturar_contacto_y_derivar_tzordan", destino_ventas

    datos_faltantes = []
    if canal == "ventas_b2b" and not contacto.get("contacto_valido"):
        datos_faltantes.append("telefono_o_email_valido")
    if tipo_cliente in {"institucion", "licitacion", "profesional_salud"}:
        datos_faltantes.extend(["nombre", "institucion_o_rol"])
    elif canal in {"ventas_b2b", "tienda_online"}:
        datos_faltantes.append("nombre")
    datos_faltantes.extend(contacto.get("errores_validacion", []))

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
        "contacto_invalido": contacto.get("errores_validacion", []),
        "es_lead_potencial": es_lead_potencial,
    }


def construir_bloque_routing(routing: dict | None) -> str:
    if not routing:
        return "Sin routing calculado. Califica la necesidad antes de derivar."
    contacto = routing.get("datos_contacto_detectados", {}) or {}
    return "\n".join([
        f"- Tipo cliente probable: {routing.get('tipo_cliente')}",
        f"- Intención probable: {routing.get('intencion')}",
        f"- Canal recomendado: {routing.get('canal_recomendado')}",
        f"- Acción comercial: {routing.get('accion')}",
        f"- Destino interno: {routing.get('destino_derivacion')}",
        f"- Producto con tienda online: {routing.get('producto_con_tienda_online')}",
        f"- Contacto válido detectado: {contacto.get('contacto_valido')}",
        f"- Errores de validación: {', '.join(routing.get('contacto_invalido', [])) or 'ninguno'}",
        f"- Datos faltantes: {', '.join(routing.get('datos_faltantes', []))}",
    ])
