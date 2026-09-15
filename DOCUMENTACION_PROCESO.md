# Documentación del proceso — Flujo Automatizacion Inventario

Guía operativa del workflow completo y del paso a paso diario.

Documentos relacionados:

- `README.md` — visión general
- `ARCHIVOS.md` — inventario de archivos del repo
- `DICCIONARIO_DATOS_EXCEL.md` — significado de columnas de `RUTAS.xlsx`
- `CHECKLIST_ENTREGA.md` — validación al cerrar el lote


==================================================
1. QUÉ HACE ESTE FLUJO (EN UNA FRASE)
==================================================

Prepara material en Drive (opcional), **clona** una carpeta a otra con
inventario y correo, y luego **registra** los archivos tipo gránulo (`G*`)
en Cloud SQL (`planner_db`), con un segundo correo de validación.


==================================================
2. WORKFLOW COMPLETO (MAPA)
==================================================

```text
[Opcional] CAMBIAR_FORMATO
    JPG/JPEG -> PNG en Drive
              |
              v
CLONACION_CARPETA
    RUTAS.xlsx
      -> clonar origen -> destino
      -> inventario Excel local
      -> Google Sheet
      -> CORREO 1 (link Sheet)
              |
              v
LMS_Fabrica
    RUTAS.xlsx (columna destino)
      -> escanear Drive
      -> CSV lms_base_rutas.csv
      -> cargar Cloud SQL (fabrica_pruebas)
      -> CORREO 2 (resumen + query SQL)
```

### Capas

| Capa | Carpeta | Entrada | Salida |
|---|---|---|---|
| Formato | `CAMBIAR_FORMATO/` | ID de carpeta Drive | PNG en Drive |
| Clonación | `CLONACION_CARPETA/` | `RUTAS.xlsx` | Carpeta destino + inventario + correo 1 |
| Carga LMS | `LMS_Fabrica/` | `RUTAS.xlsx` + destino | CSV + filas en Cloud SQL + correo 2 |

### Qué queda encadenado hoy

- **Dentro de clonación:** un solo comando dispara inventario + Sheet + correo 1.
- **Dentro de GCP:** `cargar_base_gcp.py` dispara el correo 2.
- **De punta a punta:** `run_flujo.py` en la raíz ejecuta clon → CSV → GCP
  en serie y se detiene si un paso falla.
  Con `--con-formato` también incluye JPG→PNG al inicio.


==================================================
3. PASO A PASO DIARIO
==================================================

### Opción A — Flujo continuo (recomendado)

```powershell
cd FlujoFormato_clonacion
python run_flujo.py
```

Variantes:

```powershell
python run_flujo.py --con-formato
python run_flujo.py --excel C:\Users\angie_vera\Downloads\RUTAS.xlsx
python run_flujo.py --sin-clon
python run_flujo.py --sin-gcp
python run_flujo.py --sin-correo
```

No ejecuta `clonar_esquema_pruebas.py` (fuera del flujo diario).

### Opción B — Bloques sueltos

### Paso 0 — Preparar

1. Llenar `RUTAS.xlsx` (ver `DICCIONARIO_DATOS_EXCEL.md`).
2. Guardar y **cerrar** Excel.
3. Confirmar `.env` / OAuth locales.

### Paso 1 — Formato (solo si hay JPG que deban ser PNG)

```powershell
cd CAMBIAR_FORMATO
pip install -r requirements.txt
python convertir_jpg_a_png.py
```

Antes: ajustar `ID_CARPETA` dentro del script.

### Paso 2 — Clonar + inventario + correo 1

```powershell
cd CLONACION_CARPETA
pip install -r requirements.txt
python clone_carpeta_drive.py
```

Ese comando encadena:

1. Leer Excel  
2. Clonar origen → destino  
3. Inventario  
4. Publicar Google Sheet  
5. Enviar correo 1  

### Paso 3 — Generar CSV desde el destino

```powershell
cd LMS_Fabrica
pip install -r requirements.txt
python generar_base_rutas.py --excel RUTAS.xlsx -o lms_base_rutas.csv
```

Solo indexa archivos `G` + dígitos (ej. `G1001_intro.pdf`).

### Paso 4 — Cargar a Cloud SQL (prueba) + correo 2

```powershell
python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas
```

Opciones útiles:

```powershell
# Reclasificar cliente/raíz solo en prueba
python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas --actualizar

# Cargar sin correo
python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas --sin-correo
```

### Paso 5 — Validar entrega

Completar `CHECKLIST_ENTREGA.md`.


==================================================
4. REGLAS IMPORTANTES
==================================================

1. **Destino es la verdad para GCP:** solo se escanea la columna `destino`.
2. **Dos correos distintos:** Sheet (clon) y resumen SQL (GCP). Ninguno sale solo por subir un PDF.
3. **Esquema:** diario = `fabrica_pruebas`. Producción `fabrica` solo si el equipo lo pide.
4. **No es flujo diario:** `clonar_esquema_pruebas.py` (admin, una vez) ni `comparar_clon_drive.py` (diagnóstico).
5. **Secretos fuera de Git:** `.env`, tokens, credenciales, CSV/Excel de corridas.


==================================================
5. DOS TIPOS DE CONTEO (NO CONFUNDIR)
==================================================

| Tema | Inventario del clon | Carga a GCP |
|---|---|---|
| Qué mira | Carpetas/archivos del lote | Solo archivos `G*` |
| Moodle `01_Quiz.txt` | Sí puede contar | No entra si no es `G*` |
| Salida | Excel + Google Sheet | CSV + Cloud SQL |


==================================================
6. CONFIGURACIÓN MÍNIMA
==================================================

```powershell
copy .env.example .env
```

Variables típicas:

```env
CORREOS_AVISO=correo1@cun.edu.co,correo2@cun.edu.co
DB_HOST=
DB_PORT=5432
DB_NAME=planner_db
DB_USER=
DB_PASSWORD=
LMS_SCHEMA=fabrica_pruebas
```

OAuth:

- Clonación: `CLONACION_CARPETA/credentials.json` + `token.json`
- Formato / LMS: `credenciales.json` + `token.json` en su carpeta

Si caduca el token de clonación:

```powershell
cd CLONACION_CARPETA
python renovar_token.py
```


==================================================
7. PROBLEMAS FRECUENTES
==================================================

| Síntoma | Qué revisar |
|---|---|
| No lee el Excel | Cerrar `RUTAS.xlsx` |
| URL inválida | Pegar link completo de carpeta Drive o el ID |
| No llega correo | `CORREOS_AVISO`, scope Gmail, renovar token |
| CSV vacío | Nombres `G123_...`, permisos, carpeta destino correcta |
| Cloud SQL no conecta | IP autorizada + `.env` completo |
| Token viejo | `renovar_token.py` |


==================================================
8. NOTAS DE MANTENIMIENTO
==================================================

- Orquestador: `run_flujo.py` (no incluye creación de esquema).
- LMS Correcciones: clasificación Excel → cliente PRODUCTO + raíz **LMS_Carga**.
- `clonar_esquema_pruebas.py` permanece solo para admin excepcional.

Documentación operativa — sep 2026.
