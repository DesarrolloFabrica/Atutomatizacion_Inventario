# Automatizacion Inventario (Flujo LMS)

Herramientas en Python para fabrica de contenido (CUN):
preparan material en Google Drive, lo clonan con control de calidad
y lo registran en Cloud SQL (planner_db).

Este repo **no** incluye secretos. Cada persona configura OAuth y `.env` en local.


## Primera vez en un PC nuevo

1. Instalar Python 3.10+ y las dependencias de cada carpeta (`pip install -r requirements.txt`).
2. Pedir al equipo (no están en Git): `credentials.json` / `credenciales.json` y datos del `.env`.
3. Copiar `.env.example` → `.env` y completar correos (y DB si vas a cargar GCP).
4. Colocar el JSON de Google en la carpeta del bloque que uses; al autorizar se crea `token.json`.
5. Tener el Excel `RUTAS.xlsx` (ver `DICCIONARIO_DATOS_EXCEL.md`).

Guía completa: `DOCUMENTACION_PROCESO.md`.  
Detalle por bloque: README dentro de `CAMBIAR_FORMATO/`, `CLONACION_CARPETA/`, `LMS_Fabrica/`.


## Capas del proyecto

- `CAMBIAR_FORMATO/`: convierte JPG/JPEG a PNG en Drive (**obligatorio** en el flujo diario).
- `CLONACION_CARPETA/`: clona origen → destino, genera inventario (reporte), Sheet y correo 1.
- `LMS_Fabrica/`: escanea el destino, genera CSV, carga Cloud SQL y correo 2.


## Flujo general

1. Convertir JPG a PNG (indicar carpeta con `--carpeta-formato`).
2. Leer `RUTAS.xlsx` y clonar origen → destino.
3. Inventario (reporte Excel + Google Sheet) y **correo 1**.
4. Escanear el **destino**, generar CSV.
5. Cargar Cloud SQL (`fabrica_pruebas`) y **correo 2**.

```powershell
python run_flujo.py --excel "C:\ruta\RUTAS.xlsx" --carpeta-formato "https://drive.google.com/drive/folders/TU_ID"
```

Opciones: `--sin-formato`, `--sin-clon`, `--sin-gcp`, `--sin-correo`.


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
python run_flujo.py --excel "C:\ruta\RUTAS.xlsx" --carpeta-formato "https://drive.google.com/drive/folders/TU_ID"
```

Encadena formato → clonación/inventario → CSV → Cloud SQL.


## Ejecutar formato (obligatorio en flujo diario)

```powershell
cd CAMBIAR_FORMATO
pip install -r requirements.txt
python convertir_jpg_a_png.py --carpeta "https://drive.google.com/drive/folders/TU_ID"
```

La carpeta de Drive se indica en cada corrida con `--carpeta` (enlace o ID).
Ver `CAMBIAR_FORMATO/README.md` (incluye sección “Primera vez”).


## Ejecutar clonacion + inventario + correo

```powershell
cd CLONACION_CARPETA
pip install -r requirements.txt
python clone_carpeta_drive.py --excel "C:\ruta\RUTAS.xlsx"
```

Ese unico comando encadena inventario, Google Sheets y el correo 1.
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


## Que no es flujo diario

- Crear el esquema `fabrica_pruebas` (se hace una vez).
- `clonar_esquema_pruebas.py` (solo administracion excepcional).
- `comparar_clon_drive.py` (diagnostico manual).
- `codigo.js` / `codigos.txt` (respaldo Apps Script; el oficial es Python).


## Para analistas (una frase)

Primero aseguras una copia limpia en Drive y un inventario compartido por correo;
despues traduces esa carpeta destino a un CSV y la registras en la base de prueba,
con otro correo para validar.

Guia operativa completa: `DOCUMENTACION_PROCESO.md`.
Validacion al cerrar: `CHECKLIST_ENTREGA.md`.


Documentacion del flujo operativo LMS - alineada al estilo de repos Fabrica - sep 2026.
