#!/usr/bin/env python3
"""
build_kb.py — Generador del knowledge base de Dr's Choice

Lee todos los PDFs de /pdfs/ y las URLs de urls.txt,
extrae texto y tablas estructuradas, y genera knowledge_base.json.

Uso manual:
    pip install pdfplumber requests beautifulsoup4
    python build_kb.py

Se ejecuta automáticamente vía GitHub Actions en cada push
que modifique /pdfs/ o urls.txt.
"""

import json
import os
import re
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

try:
    import pdfplumber
except ImportError:
    print("⚠️  pdfplumber no instalado. Ejecuta: pip install pdfplumber")
    raise

# ── Configuración ─────────────────────────────────────────────
PDFS_DIR    = Path("pdfs")
URLS_FILE   = Path("urls.txt")
OUTPUT_FILE = Path("knowledge_base.json")
KB_BASE     = Path("brandbook.json")  # datos estáticos de empresa/brandbook

# ── 1. Cargar datos base (empresa, brandbook, servicios) ──────

def cargar_base() -> dict:
    """
    Carga el JSON base con datos estáticos del brandbook:
    empresa, áreas, segmentos, propuesta de valor, etc.
    Estos datos NO vienen de los PDFs — se mantienen a mano.
    """
    if KB_BASE.exists():
        with open(KB_BASE, encoding="utf-8") as f:
            return json.load(f)
    # Si no existe la base, retornamos estructura mínima
    print("⚠️  brandbook.json no encontrado — usando estructura mínima")
    return {
        "empresa": {
            "nombre": "Dr's Choice",
            "fundacion": 1992,
            "slogan": "Nos mueve tu bienestar",
            "whatsapp": "+56 9 6159 8525",
            "email": "serviciocliente@doctorchoice.cl",
            "web": "https://drchoice.cl",
            "direccion": "Miguel Claro 954, Providencia, Santiago"
        },
        "areas": {},
        "segmentos": {},
        "propuesta_de_valor": {},
        "chatbot": {},
        "mensajes_clave": {},
        "keywords_rag": [],
        "intents": {},
        "variables_crm": {},
        "servicios": []
    }

# ── 2. Extracción de PDFs ─────────────────────────────────────

def extraer_tablas_pdf(page) -> list[dict]:
    """
    Extrae tablas de una página PDF y las convierte en
    lista de dicts con los headers como claves.
    """
    tablas = []
    for tabla in page.extract_tables():
        if not tabla or len(tabla) < 2:
            continue
        headers = [str(h).strip().lower().replace(" ", "_") if h else f"col_{i}"
                   for i, h in enumerate(tabla[0])]
        for fila in tabla[1:]:
            if any(c for c in fila):  # descartamos filas vacías
                row = {headers[i]: str(v).strip() if v else ""
                       for i, v in enumerate(fila)}
                tablas.append(row)
    return tablas


def limpiar_texto(texto: str) -> str:
    """Limpia el texto extraído de ruido tipográfico."""
    if not texto:
        return ""
    # Elimina saltos de línea múltiples
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    # Elimina espacios múltiples
    texto = re.sub(r" {2,}", " ", texto)
    # Elimina líneas con solo números de página o guiones
    texto = re.sub(r"^\s*[\d\-–—]+\s*$", "", texto, flags=re.MULTILINE)
    return texto.strip()


def detectar_catalogo(nombre_archivo: str) -> str:
    """Detecta el tipo de catálogo según el nombre del archivo."""
    nombre = nombre_archivo.lower()
    if "ortesis" in nombre or "órtesis" in nombre:
        return "ortesis"
    elif "rehabilitacion" in nombre or "rehabilitación" in nombre or "insumos" in nombre:
        return "rehabilitacion"
    elif "tecnolog" in nombre:
        return "tecnologias"
    return "general"


def procesar_pdf(pdf_path: Path) -> dict:
    """
    Extrae texto y tablas de un PDF.
    Retorna dict con:
    - texto_completo: todo el texto del PDF
    - tablas: todas las tablas extraídas
    - paginas: número de páginas
    - catalogo: tipo detectado
    - fuente: nombre del archivo
    """
    catalogo = detectar_catalogo(pdf_path.name)
    texto_paginas = []
    todas_tablas = []

    print(f"  📄 Procesando {pdf_path.name}...")

    with pdfplumber.open(pdf_path) as pdf:
        n_paginas = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            # Texto
            texto = page.extract_text(x_tolerance=3, y_tolerance=3)
            if texto:
                texto_paginas.append(limpiar_texto(texto))

            # Tablas
            tablas = extraer_tablas_pdf(page)
            for tabla in tablas:
                tabla["_pagina"] = i + 1
                tabla["_catalogo"] = catalogo
                todas_tablas.append(tabla)

    texto_completo = "\n\n".join(texto_paginas)
    print(f"    ✅ {n_paginas} páginas | {len(texto_completo)} chars | {len(todas_tablas)} filas de tablas")

    return {
        "fuente": pdf_path.name,
        "catalogo": catalogo,
        "paginas": n_paginas,
        "texto_completo": texto_completo,
        "tablas": todas_tablas
    }


def extraer_productos_de_texto(texto: str, catalogo: str) -> list[dict]:
    """
    Usa heurísticas para identificar productos en el texto extraído.
    Busca patrones como SKU, nombres de productos, descripciones.
    
    Para catálogos bien estructurados esto funciona bien.
    Para PDFs con layouts complejos, puede requerir ajuste manual.
    """
    productos = []
    
    # Patrón básico: busca bloques que parezcan fichas de producto
    # Ajustar según la estructura real de los PDFs de Dr's Choice
    bloques = re.split(r"\n(?=[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑA-Za-záéíóúñ\s]{5,})\n", texto)
    
    for bloque in bloques:
        bloque = bloque.strip()
        if len(bloque) < 30:
            continue
            
        # Busca SKU (patrones comunes en catálogos médicos)
        sku_match = re.search(
            r"(?:SKU|Ref\.?|Código|Code)[:\s]+([A-Z0-9\-\.\/]+)",
            bloque, re.IGNORECASE
        )
        
        if sku_match:
            sku = sku_match.group(1).strip()
            # Primera línea como nombre del producto
            lineas = [l.strip() for l in bloque.split("\n") if l.strip()]
            nombre = lineas[0] if lineas else "Producto sin nombre"
            descripcion = " ".join(lineas[1:5]) if len(lineas) > 1 else ""
            
            productos.append({
                "nombre": nombre,
                "sku": sku,
                "catalogo": catalogo,
                "categoria": "",
                "marca": None,
                "descripcion": limpiar_texto(descripcion),
                "indicaciones": [],
                "stock": "consultar",
                "_fuente_auto": True  # marcamos como extraído automáticamente
            })
    
    return productos


# ── 3. Web Scraping ───────────────────────────────────────────

def cargar_urls() -> list[str]:
    """Lee las URLs desde urls.txt — una por línea, # para comentarios."""
    if not URLS_FILE.exists():
        print(f"⚠️  {URLS_FILE} no encontrado — sin web scraping")
        return []
    
    urls = []
    with open(URLS_FILE, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea and not linea.startswith("#"):
                urls.append(linea)
    
    print(f"📋 {len(urls)} URLs cargadas desde {URLS_FILE}")
    return urls


def scrape_url(url: str, timeout: int = 10) -> dict:
    """Extrae texto limpio de una URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; DrChoice-KB/2.0)"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Eliminamos ruido
        for tag in soup(["script", "style", "nav", "footer", "header", "meta"]):
            tag.decompose()
        
        texto = soup.get_text(separator=" ", strip=True)
        texto = re.sub(r"\s{2,}", " ", texto).strip()
        
        print(f"  🌐 {url} → {len(texto)} chars")
        return {
            "url": url,
            "texto": texto[:3000],  # máximo 3000 chars por URL
            "ok": True
        }
    except Exception as e:
        print(f"  ⚠️  {url} → Error: {e}")
        return {"url": url, "texto": "", "ok": False}


# ── 4. Ensamblado del KB ──────────────────────────────────────

def construir_knowledge_base() -> dict:
    """
    Proceso completo:
    1. Carga datos base (brandbook, empresa)
    2. Procesa todos los PDFs en /pdfs/
    3. Scrapea todas las URLs en urls.txt
    4. Ensambla el knowledge_base.json final
    """
    print("\n" + "="*60)
    print("CONSTRUYENDO KNOWLEDGE BASE — Dr's Choice")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # ── Paso 1: datos base ────────────────────────────────────
    kb = cargar_base()
    kb["_generado_en"] = datetime.now().isoformat()
    kb["_fuentes"] = []

    # ── Paso 2: procesar PDFs ─────────────────────────────────
    productos_extraidos = []
    chunks_pdf = []

    if PDFS_DIR.exists():
        pdfs = sorted(PDFS_DIR.glob("*.pdf"))
        print(f"\n📂 PDFs encontrados: {len(pdfs)}")
        
        for pdf_path in pdfs:
            resultado = procesar_pdf(pdf_path)
            kb["_fuentes"].append({
                "tipo": "pdf",
                "archivo": pdf_path.name,
                "paginas": resultado["paginas"],
                "catalogo": resultado["catalogo"]
            })
            
            # Guardamos el texto completo como chunk para RAG
            chunks_pdf.append({
                "fuente": pdf_path.name,
                "catalogo": resultado["catalogo"],
                "texto": resultado["texto_completo"][:5000],
                "tablas": resultado["tablas"]
            })
            
            # Intentamos extraer productos estructurados
            prods = extraer_productos_de_texto(
                resultado["texto_completo"],
                resultado["catalogo"]
            )
            if prods:
                productos_extraidos.extend(prods)
                print(f"    → {len(prods)} productos detectados automáticamente")
    else:
        print(f"\n⚠️  Carpeta {PDFS_DIR} no encontrada — sin procesamiento de PDFs")

    # ── Paso 3: web scraping ──────────────────────────────────
    urls = cargar_urls()
    chunks_web = []
    
    if urls:
        print(f"\n🌐 Scrapeando {len(urls)} URLs...")
        for url in urls:
            resultado = scrape_url(url)
            if resultado["ok"] and resultado["texto"]:
                chunks_web.append(resultado)
                kb["_fuentes"].append({"tipo": "web", "url": url})

    # ── Paso 4: ensamblado ────────────────────────────────────
    # Productos: combinamos los existentes en la base + los extraídos de PDFs
    # Los de la base tienen prioridad (son curados manualmente)
    productos_base = kb.get("productos", [])
    skus_base = {p["sku"] for p in productos_base}
    
    # Solo agregamos los extraídos automáticamente si no están ya en la base
    productos_nuevos = [p for p in productos_extraidos if p["sku"] not in skus_base]
    if productos_nuevos:
        print(f"\n✨ {len(productos_nuevos)} productos nuevos detectados en PDFs")
    
    kb["productos"] = productos_base + productos_nuevos
    kb["_chunks_pdf"] = chunks_pdf
    kb["_chunks_web"] = chunks_web
    
    print(f"\n📊 Resumen:")
    print(f"   Productos: {len(kb['productos'])} ({len(productos_base)} base + {len(productos_nuevos)} nuevos)")
    print(f"   Chunks PDF: {len(chunks_pdf)}")
    print(f"   Chunks web: {len(chunks_web)}")
    print(f"   Fuentes totales: {len(kb['_fuentes'])}")
    
    return kb


# ── 5. Main ───────────────────────────────────────────────────

if __name__ == "__main__":
    kb = construir_knowledge_base()
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ {OUTPUT_FILE} generado exitosamente")
    print(f"   Tamaño: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")
