# Automatizacion Inventario (Flujo LMS)

Herramientas en Python para fabrica de contenido (CUN):
preparan material en Google Drive, lo clonan con control de calidad
y lo registran en Cloud SQL (planner_db).

Este repo NO incluye secretos. Cada persona configura OAuth y `.env` en local.


## Capas del proyecto

El flujo tiene tres bloques (capas operativas):

- `CAMBIAR_FORMATO/`: convierte JPG/JPEG a PNG en Drive (**obligatorio** en el flujo diario).
- `CLONACION_CARPETA/`: clona origen -> destino, inventaria, publica Google Sheet
  y envia correo Gmail con el link del inventario.
- `LMS_Fabrica/`: escanea el destino, genera CSV y carga a Cloud SQL;
  al final envia correo Gmail con resumen + query SQL.

Documentacion extra por carpeta y listado de archivos:

- `DOCUMENTACION_PROCESO.md` — workflow completo + paso a paso
- `DICCIONARIO_DATOS_EXCEL.md` — columnas de `RUTAS.xlsx`
- `CHECKLIST_ENTREGA.md` — validacion al cerrar el lote
- `CAMBIAR_FORMATO/README.md`
- `CLONACION_CARPETA/README.md`
- `LMS_Fabrica/README.md`
- `ARCHIVOS.md`


## Flujo general

1. Convertir JPG a PNG en Drive (`--carpeta` / `--carpeta-formato`).
2. Leer `RUTAS.xlsx` y clonar carpeta origen -> destino.
3. Generar inventario (Excel local + Google Sheet) y enviar **correo 1**.
4. Escanear solo el **destino**, generar CSV intermedio.
5. Cargar CSV a Cloud SQL (`fabrica_pruebas`) y enviar **correo 2**.

El inventario va **después** del clon (compara origen vs destino).

```powershell
python run_flujo.py --carpeta-formato <ID_o_URL_Drive>
```

Opciones: `--excel RUTA`, `--sin-formato`, `--sin-clon`, `--sin-gcp`, `--sin-correo`.
Detalle en `DOCUMENTACION_PROCESO.md`.


## Estructura actual

```text
./
├── run_flujo.py                        # orquestador del flujo diario
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
Cliente/origen/destino salen del Excel (no hay diccionario hardcodeado de programas).


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
python run_flujo.py --carpeta-formato <ID_o_URL_Drive>
```

Encadena formato → clonación/inventario → CSV → Cloud SQL.


## Ejecutar formato (obligatorio en flujo diario)

```powershell
cd CAMBIAR_FORMATO
pip install -r requirements.txt
python convertir_jpg_a_png.py --carpeta <ID_o_URL_Drive>
```

La carpeta se pasa por argumento (no hay ID hardcodeado en el script).


## Ejecutar clonacion + inventario + correo

```powershell
cd CLONACION_CARPETA
pip install -r requirements.txt
python clone_carpeta_drive.py
```

Ese unico comando encadena inventario, Google Sheets y el correo 1.
La ruta de `RUTAS.xlsx` esta fija en el codigo; cambiala si usas otro PC.


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
