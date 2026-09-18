# LMS_Fabrica — Escaneo Drive y carga a Cloud SQL

Toma las carpetas **destino** del Excel, genera un CSV y registra los archivos
en Cloud SQL (`planner_db`). Al terminar envía el **correo 2**.

Esquema diario: `fabrica_pruebas`.  
Producción (`fabrica`) solo si el equipo lo pide explícitamente.

## Primera vez (configuración)

1. Instalar dependencias:

```powershell
cd LMS_Fabrica
pip install -r requirements.txt
```

2. Copiar `.env.example` → `.env` y completar:
   - `CORREOS_AVISO`
   - `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
   - `LMS_SCHEMA=fabrica_pruebas`

3. Colocar en esta carpeta (no van a Git):
   - `credenciales.json` — OAuth Desktop
   - `token.json` — sesión de Google

4. La IP de tu PC debe estar autorizada en Cloud SQL (si vas a cargar).

## Uso diario (dos pasos)

```powershell
cd LMS_Fabrica
python generar_base_rutas.py --excel "C:\ruta\RUTAS.xlsx" -o lms_base_rutas.csv
python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas
```

- Paso 1: escanea Drive (columna **destino** del Excel) y genera el CSV  
- Paso 2: inserta en Cloud SQL y envía el correo 2  

Sin correo:

```powershell
python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas --sin-correo
```

## Qué entra al CSV / base

- Si el archivo empieza con `G` + números → ese es el código (ej. `G1001`)
- Si no (Moodle u otros) → se usa el nombre sin extensión (ej. `01_Quiz`)
- Cliente, origen y destino salen del Excel (no hay lista fija de programas en el código)

## Excel → valores en GCP

| Valor en Excel | cliente en GCP | raíz en GCP |
|---|---|---|
| PRODUCTO | PRODUCTO | LMS_Carga |
| TANIA | TANIA | LMS_Carga |
| LMS_correcciones | PRODUCTO | LMS_Carga |

## Scripts

| Script | Rol |
|---|---|
| `generar_base_rutas.py` | Paso 1 diario (Excel → CSV) |
| `cargar_base_gcp.py` | Paso 2 diario (CSV → Cloud SQL + correo) |
| `notificar_carga_lms.py` | Correo 2 (lo dispara la carga) |
| `generar_base_lms.py` | Librería compartida |
| `lms_lib/` | Constantes compartidas |
| `clonar_esquema_pruebas.py` | Admin, **una sola vez** (NO diario) |

## No subir a Git

`credenciales.json`, `token.json`, `.env`, CSV de corridas.
