# Documentación del proceso — Flujo Automatizacion Inventario

Guía operativa. Ver también: `README.md`, `DICCIONARIO_DATOS_EXCEL.md`, `CHECKLIST_ENTREGA.md`.


==================================================
1. QUÉ HACE ESTE FLUJO
==================================================

Convierte JPG→PNG en Drive, **clona** origen→destino con inventario y correo,
y **registra** archivos del destino en Cloud SQL (`planner_db`), con un segundo correo.


==================================================
2. WORKFLOW COMPLETO
==================================================

```text
1) CAMBIAR_FORMATO  (obligatorio)
    JPG/JPEG -> PNG en Drive
    Entrada: --carpeta (enlace o ID de la carpeta en Drive)
              |
              v
2) CLONACION_CARPETA
    Lee: RUTAS.xlsx (indicar con --excel o variable RUTAS_XLSX)
         (columnas: cliente | etiqueta | origen | destino)
      -> clonar origen -> destino (en Drive)
      -> inventario Excel local:
           CLONACION_CARPETA\reporte_inventario_clon.xlsx
           (compara qué hay en origen vs qué quedó en destino)
      -> publica ese inventario en Google Sheet
      -> CORREO 1 (link de la Sheet)
              |
              v
3) LMS_Fabrica
    Lee el mismo RUTAS.xlsx (solo columna destino)
      -> escanear esa carpeta en Drive
      -> CSV: LMS_Fabrica\lms_base_rutas.csv
      -> cargar Cloud SQL (fabrica_pruebas)
      -> CORREO 2 (resumen + query SQL)
```

**Inventario** = reporte de control de calidad del clon (conteos, Moodle, faltantes…),  
**no** es el CSV de carga a GCP.

Orden: clonar → inventario → Sheet → correo 1.  
JPG→PNG va antes del clon y es obligatorio.

| Capa | Carpeta | Entrada | Salida |
|---|---|---|---|
| Formato | `CAMBIAR_FORMATO/` | Enlace o ID de carpeta Drive | PNG en Drive |
| Clonación | `CLONACION_CARPETA/` | `RUTAS.xlsx` | Destino + inventario + correo 1 |
| Carga LMS | `LMS_Fabrica/` | `RUTAS.xlsx` (destino) | CSV + Cloud SQL + correo 2 |

Orquestador: `python run_flujo.py --carpeta-formato "https://drive.google.com/drive/folders/TU_ID"`
No ejecuta `clonar_esquema_pruebas.py` (admin, una sola vez).


==================================================
3. PASO A PASO DIARIO
==================================================

### Opción A — Flujo continuo

```powershell
cd FlujoFormato_clonacion
python run_flujo.py --carpeta-formato "https://drive.google.com/drive/folders/TU_ID"
```

Variantes: `--excel RUTA`, `--sin-formato`, `--sin-clon`, `--sin-gcp`, `--sin-correo`.

### Opción B — Bloques sueltos

1. Llenar y cerrar `RUTAS.xlsx`. Confirmar `.env` / OAuth.
2. Formato:

```powershell
cd CAMBIAR_FORMATO
python convertir_jpg_a_png.py --carpeta "https://drive.google.com/drive/folders/TU_ID"
```

3. Clonar + inventario + correo 1:

```powershell
cd CLONACION_CARPETA
python clone_carpeta_drive.py
```

4. CSV desde destino:

```powershell
cd LMS_Fabrica
python generar_base_rutas.py --excel RUTAS.xlsx -o lms_base_rutas.csv
```

5. Cargar Cloud SQL + correo 2:

```powershell
python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas
```

6. Completar `CHECKLIST_ENTREGA.md`.


==================================================
4. REGLAS IMPORTANTES
==================================================

1. **Destino** es lo que se escanea para GCP.
2. Dos correos: Sheet (clon) y SQL (GCP).
3. Esquema diario: `fabrica_pruebas`.
4. Fuera del flujo diario: `clonar_esquema_pruebas.py`, `comparar_clon_drive.py`.
5. No versionar secretos (`.env`, tokens, credenciales).
6. Clientes Drive: `PRODUCTO`, `TANIA`, `LMS_CORRECCIONES` (en GCP correcciones → PRODUCTO).
7. Indexación: si hay `G`+dígitos se usa; si no (Moodle, etc.), el stem del archivo.


==================================================
5. DOS TIPOS DE CONTEO
==================================================

| Tema | Inventario del clon | Carga a GCP |
|---|---|---|
| Qué mira | Carpetas/archivos del lote | Archivos con ruta válida (G* o stem) |
| Moodle `01_Quiz.txt` | Sí cuenta | Sí entra (código = stem) |
| Salida | Excel + Google Sheet | CSV + Cloud SQL |


==================================================
6. CONFIGURACIÓN MÍNIMA
==================================================

```powershell
copy .env.example .env
```

```env
CORREOS_AVISO=correo1@cun.edu.co,correo2@cun.edu.co
DB_HOST=
DB_PORT=5432
DB_NAME=planner_db
DB_USER=
DB_PASSWORD=
LMS_SCHEMA=fabrica_pruebas
```

OAuth: `credentials.json`/`credenciales.json` + `token.json` en cada bloque.
Si caduca el token de clonación: `cd CLONACION_CARPETA` → `python renovar_token.py`.


==================================================
7. PROBLEMAS FRECUENTES
==================================================

| Síntoma | Qué revisar |
|---|---|
| No lee el Excel | Cerrar `RUTAS.xlsx` |
| URL inválida | Link completo de carpeta Drive o el ID |
| No llega correo | `CORREOS_AVISO`, scope Gmail, renovar token |
| CSV vacío | Estructura de carpetas, permisos, columna destino |
| Cloud SQL no conecta | IP autorizada + `.env` |
| Formato falla | Indicar `--carpeta` / `--carpeta-formato` con el enlace o ID de la carpeta |


==================================================
8. MANTENIMIENTO
==================================================

- Orquestador: `run_flujo.py` (no crea esquema DB).
- Constantes LMS: `LMS_Fabrica/lms_lib/constantes.py`.
- LMS Correcciones (Excel) → cliente PRODUCTO + raíz LMS_Carga.
- `clonar_esquema_pruebas.py` solo admin excepcional (no es flujo diario).
