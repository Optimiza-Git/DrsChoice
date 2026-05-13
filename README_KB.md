# Knowledge Base — Dr's Choice

## Cómo funciona

El `knowledge_base.json` se genera **automáticamente** cada vez que se hace push con cambios en:
- `pdfs/` — catálogos de productos en PDF
- `urls.txt` — páginas web a indexar
- `brandbook.json` — datos estáticos del brandbook

**No editar `knowledge_base.json` directamente** — los cambios se sobreescriben en el próximo build.

## Agregar un producto nuevo

### Opción A — PDF completo (catálogo nuevo)
1. Agregar el PDF en la carpeta `pdfs/`
2. Hacer push → GitHub Actions regenera el KB automáticamente

### Opción B — Producto individual
1. Editar `brandbook.json` y agregar el producto en la lista `productos`
2. Hacer push → GitHub Actions regenera el KB

## Agregar una URL nueva
1. Editar `urls.txt` y agregar la URL en una línea nueva
2. Hacer push → GitHub Actions regenera el KB

## Estructura de archivos

```
pdfs/                          ← PDFs del cliente (fuente de verdad)
urls.txt                       ← URLs a scrapear (una por línea)
brandbook.json       ← datos estáticos: empresa, brandbook, servicios
knowledge_base.json            ← generado automáticamente ⚠️ no editar
build_kb.py                    ← script que genera el KB
.github/workflows/build_kb.yml ← automatización
```
