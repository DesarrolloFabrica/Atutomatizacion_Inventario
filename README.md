# Automatizacion Inventario (Flujo LMS)

Proyecto de automatización para la fábrica de contenido (CUN).
Prepara material en Google Drive, ejecuta la clonación con control de calidad
y registra el resultado en Cloud SQL (`planner_db`).

El repositorio no incluye secretos. La configuración OAuth y el archivo `.env`
se definen en el entorno local de ejecución.


## Requisitos de entorno

1. Python 3.10 o superior y dependencias de cada módulo (`pip install -r requirements.txt`).
2. Credenciales OAuth de Google (`credentials.json` / `credenciales.json`) y generación de `token.json`.
3. Archivo `.env` a partir de `.env.example` (notificaciones y, para carga, parámetros de base de datos).
4. Archivo `RUTAS.xlsx` conforme a `DICCIONARIO_DATOS_EXCEL.md`.

Documentación operativa: `DOCUMENTACION_PROCESO.md`.  
Documentación por módulo: `CAMBIAR_FORMATO/README.md`, `CLONACION_CARPETA/README.md`, `LMS_Fabrica/README.md`.


## Módulos

- `CAMBIAR_FORMATO/`: conversión JPG/JPEG → PNG en Drive (paso inicial del flujo).
- `CLONACION_CARPETA/`: clonación origen → destino, inventario (reporte), Sheet y correo 1.
- `LMS_Fabrica/`: escaneo del destino, CSV, carga a Cloud SQL y correo 2.


## Flujo general

1. Conversión JPG → PNG (`--carpeta-formato`).
2. Lectura de `RUTAS.xlsx` y clonación origen → destino.
3. Inventario (reporte Excel + Google Sheet) y correo 1.
4. Escaneo del destino y generación del CSV.
5. Carga a Cloud SQL (`fabrica_pruebas`) y correo 2.

```powershell
python run_flujo.py --excel "<RUTA>\RUTAS.xlsx" --carpeta-formato "https://drive.google.com/drive/folders/<ID_CARPETA>"
```

Parámetros adicionales: `--sin-formato`, `--sin-clon`, `--sin-gcp`, `--sin-correo`.


## Estructura actual

```text
./
├── run_flujo.py                        # orquestador del flujo diario
├── rutas_excel.py                      # localiza RUTAS.xlsx sin rutas fijas
├── CAMBIAR_FORMATO/
│   ├── convertir_jpg_a_png.py
│   ├── codigo.js
│   ├── codigos.txt
│   ├── requirements.txt
│   └── README.md
├── CLONACION_CARPETA/
│   ├── clone_carpeta_drive.py          # clon + reporte inventario + correo 1
│   ├── reporte_inventario_clon.py
│   ├── publicar_inventario_sheets.py
│   ├── notificar_clonacion.py
│   ├── renovar_token.py
│   ├── comparar_clon_drive.py          # diagnostico (no diario)
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
├── LMS_Fabrica/
│   ├── generar_base_rutas.py           # Excel -> Drive -> CSV
│   ├── cargar_base_gcp.py              # CSV -> Cloud SQL + correo 2
│   ├── notificar_carga_lms.py
│   ├── generar_base_lms.py             # libreria compartida (API publica)
│   ├── lms_lib/                        # constantes compartidas
│   ├── clonar_esquema_pruebas.py       # admin una vez (NO diario)
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
├── .env.example
├── .gitignore
├── DOCUMENTACION_PROCESO.md
├── DICCIONARIO_DATOS_EXCEL.md
├── CHECKLIST_ENTREGA.md
├── ARCHIVOS.md
└── README.md
```


## Que NO va en el repositorio

Estas cosas se generan en local o son secretos; estan en `.gitignore`:

- `credentials.json` / `credenciales.json`
- `token.json`
- `.env`
- `clonacion.log`, `hoja_inventario_id.txt`
- CSV/Excel de corridas (`lms_base_rutas.csv`, `RUTAS.xlsx`, reportes)
- `__pycache__/`, `.venv/`

En runtime:

- El inventario local y la Sheet se actualizan al clonar.
- El CSV se crea al generar la base; no se versiona.


## Excel RUTAS.xlsx

Una fila = un lote.

- `etiqueta`: apodo humano (no se guarda en GCP).
- `origen`: carpeta a clonar (en carga GCP solo es referencia).
- `destino`: carpeta destino; en carga GCP es la **unica** que se escanea.
- `cliente`: `PRODUCTO`, `TANIA` o `LMS_correcciones`.

Detalle completo de columnas, valores y mapeo a GCP:
ver `DICCIONARIO_DATOS_EXCEL.md`.

El nombre del **programa** en GCP sale del nombre de la carpeta en Drive.
Cliente, origen y destino se toman del Excel.


## Dos reglas distintas

Inventario del clon:

- Cuenta por tipo de carpeta (Moodle, contenidos, SCORM, PDF, etc.).
- Archivos tipo `01_Quiz.txt` en ACTIVIDADES MOODLE **si** cuentan.

Carga a GCP:

- Si el nombre empieza con `G` + digitos, ese es el codigo.
- Si no (Moodle u otros), se usa el stem del archivo.


## Correos (hay dos)

Despues del clon (`notificar_clonacion.py`):

- Link de la Google Sheet del inventario.

Despues de cargar GCP (`notificar_carga_lms.py`):

- Resumen del lote + query SQL para Cloud SQL Studio.

Ninguno se dispara solo por subir un PDF a Drive.
Destinatarios: `CORREOS_AVISO` en `.env`.


## Variables de entorno

Copia la plantilla:

```text
copy .env.example .env
```

O usa la de cada bloque (`CLONACION_CARPETA/.env.example`, `LMS_Fabrica/.env.example`).

Configura (ejemplo PowerShell):

```powershell
$env:CORREOS_AVISO="correo1@cun.edu.co,correo2@cun.edu.co"
$env:DB_HOST="TU_HOST"
$env:DB_PORT="5432"
$env:DB_NAME="planner_db"
$env:DB_USER="TU_USUARIO"
$env:DB_PASSWORD="TU_PASSWORD"
$env:LMS_SCHEMA="fabrica_pruebas"
```

Tambien puede ir en archivo `.env`:

```env
CORREOS_AVISO=correo1@cun.edu.co,correo2@cun.edu.co
DB_HOST=
DB_PORT=5432
DB_NAME=planner_db
DB_USER=
DB_PASSWORD=
LMS_SCHEMA=fabrica_pruebas
```

Para Google Drive / Gmail / Sheets (desarrollo local) se usan OAuth Desktop:

- Clonacion: `CLONACION_CARPETA/credentials.json` + `token.json`
- Formato / LMS: `credenciales.json` + `token.json` en su carpeta

Scopes habituales: Drive, Sheets, Gmail send.
Si el token caduca o falta permiso de correo:

```powershell
cd CLONACION_CARPETA
python renovar_token.py
```

En nube o equipo compartido: secretos fuera del repo (nunca versionar
`token.json`, `credentials.json` ni `.env`).


## Requisitos

- Python 3.10+
- Acceso a las carpetas Drive del lote
- Para carga GCP: IP autorizada en Cloud SQL + `.env` completo


## Ejecutar flujo continuo (recomendado)

```powershell
python run_flujo.py --excel "<RUTA>\RUTAS.xlsx" --carpeta-formato "https://drive.google.com/drive/folders/<ID_CARPETA>"
```

Encadena formato → clonación/inventario → CSV → Cloud SQL.


## Ejecutar formato (paso inicial del flujo)

```powershell
cd CAMBIAR_FORMATO
pip install -r requirements.txt
python convertir_jpg_a_png.py --carpeta "https://drive.google.com/drive/folders/<ID_CARPETA>"
```

La carpeta de Drive se indica en cada corrida con `--carpeta` (enlace o ID).
Ver `CAMBIAR_FORMATO/README.md`.


## Ejecutar clonacion + inventario + correo

```powershell
cd CLONACION_CARPETA
pip install -r requirements.txt
python clone_carpeta_drive.py --excel "<RUTA>\RUTAS.xlsx"
```

Ese comando encadena inventario, Google Sheets y el correo 1.
Ver `CLONACION_CARPETA/README.md`.


## Ejecutar carga a GCP

```powershell
cd LMS_Fabrica
pip install -r requirements.txt
python generar_base_rutas.py --excel RUTAS.xlsx -o lms_base_rutas.csv
python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas
```

Reclasificar cliente/raiz en prueba (no permitido en produccion `fabrica`):

```powershell
python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas --actualizar
```

Omitir correo:

```powershell
python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas --sin-correo
```


## Fuera del flujo diario

- Creación del esquema `fabrica_pruebas` (actividad administrativa puntual)
- `clonar_esquema_pruebas.py`
- `comparar_clon_drive.py` (diagnóstico)
- `codigo.js` / `codigos.txt` (alternativa Apps Script; la ejecución oficial es Python)

Documentación operativa: `DOCUMENTACION_PROCESO.md`.  
Validación de entrega: `CHECKLIST_ENTREGA.md`.
