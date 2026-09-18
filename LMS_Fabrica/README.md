# LMS_Fabrica — Escaneo Drive y carga a Cloud SQL

RUTAS.xlsx (destino) → CSV → Cloud SQL → correo Gmail.

Esquema diario: `fabrica_pruebas`. Producción `fabrica` solo si el equipo lo pide.

## Scripts diarios

- `generar_base_rutas.py` — Excel → Drive → CSV
- `cargar_base_gcp.py` — CSV → Cloud SQL + correo
- `notificar_carga_lms.py` — correo (encadenado)
- `generar_base_lms.py` — API pública (auth, parsers, IDs)
- `lms_lib/constantes.py` — constantes compartidas

`clonar_esquema_pruebas.py` **no** es flujo diario (admin, una sola vez).

## Paso a paso

```powershell
cd LMS_Fabrica
pip install -r requirements.txt
python generar_base_rutas.py --excel RUTAS.xlsx -o lms_base_rutas.csv
python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas
```

## Excel → GCP

| Excel | cliente GCP | raíz GCP |
|---|---|---|
| PRODUCTO | PRODUCTO | LMS_Carga |
| TANIA | TANIA | LMS_Carga |
| LMS_correcciones | PRODUCTO | LMS_Carga |

Indexación: `G`+dígitos si existe; si no, stem del archivo (Moodle, etc.).
Origen, destino y cliente salen del Excel.

## Configuración

Copiar `.env.example` → `.env` (`CORREOS_AVISO`, `DB_*`, `LMS_SCHEMA`).
OAuth: `credenciales.json` + `token.json` (NO Git).
