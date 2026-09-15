# LMS_Fabrica - Escaneo Drive y carga a Cloud SQL

Toma carpetas ya preparadas en Drive (columna DESTINO del Excel),
genera un CSV y registra los archivos tipo granulo en PostgreSQL (Cloud SQL).

Ver tambien:
  ../README.md
  ../ARCHIVOS.md
  ../DOCUMENTACION_PROCESO.md
  ../DICCIONARIO_DATOS_EXCEL.md
  ../CHECKLIST_ENTREGA.md

Esquema por defecto: fabrica_pruebas
Produccion: fabrica (solo si el equipo lo pide)


--------------------------------------------------
FLUJO EN UNA FRASE
--------------------------------------------------

  RUTAS.xlsx -> escanear DESTINO -> CSV -> Cloud SQL -> correo Gmail

  generar_base_rutas.py   -> CSV (sin correo)
  cargar_base_gcp.py      -> GCP + notificar_carga_lms.py

El correo NO se dispara por subir un PDF a Drive.
Solo al terminar cargar_base_gcp.py


--------------------------------------------------
SCRIPTS DE ESTA CARPETA
--------------------------------------------------

  generar_base_rutas.py      Paso 1 diario (Excel -> Drive -> CSV)
  cargar_base_gcp.py         Paso 2 diario (CSV -> Cloud SQL + correo)
  notificar_carga_lms.py     Encadenado (correo Gmail)
  generar_base_lms.py        Libreria (auth, parsers, columnas, IDs)
  clonar_esquema_pruebas.py  NO diario (crear esquema una vez / admin)

Todos tienen comentarios tutorial en el codigo.


--------------------------------------------------
METADATA_EXTRA
--------------------------------------------------

Diccionario de apoyo (escuela/cliente).
NO son filas a escanear.
Solo se procesa lo del Excel.
El cliente del Excel gana sobre ese diccionario.


--------------------------------------------------
PASO A PASO
--------------------------------------------------

1) Llenar RUTAS.xlsx y CERRAR Excel

2) Generar CSV:

     cd LMS_Fabrica
     pip install -r requirements.txt
     python generar_base_rutas.py --excel RUTAS.xlsx -o lms_base_rutas.csv

3) Cargar a prueba:

     python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas

   Reclasificar cliente/raiz en prueba:

     python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas --actualizar

   --actualizar NO se permite en --schema fabrica

4) Validar con el correo / Cloud SQL Studio


--------------------------------------------------
EXCEL -> VALORES EN GCP
--------------------------------------------------

  PRODUCTO           -> cliente PRODUCTO , raiz LMS_Carga
  TANIA              -> cliente TANIA    , raiz LMS_Carga
  LMS_correcciones   -> cliente PRODUCTO , raiz LMS_Carga

LMS_correcciones es clasificación de lote, no carpeta raíz.

Solo archivos G + digitos entran al CSV/base.


--------------------------------------------------
CONFIGURACION
--------------------------------------------------

Copia .env.example -> .env

  CORREOS_AVISO=correo1@cun.edu.co
  DB_HOST=...
  DB_PORT=5432
  DB_NAME=planner_db
  DB_USER=...
  DB_PASSWORD=...
  LMS_SCHEMA=fabrica_pruebas

OAuth: credenciales.json + token.json
(scopes Drive / Sheets / Gmail send)


--------------------------------------------------
MODELO DE DATOS
--------------------------------------------------

  escuela -> programa -> materia -> granulo -> archivo

Anti-duplicados: el ENLACE del archivo.
Si ya existe, no se inserta otra vez.


--------------------------------------------------
PROBLEMAS FRECUENTES
--------------------------------------------------

  Falta OAuth          -> pedir credenciales.json al admin
  Cero archivos G      -> nombres G123_... + jerarquia + permisos
  No llega correo      -> CORREOS_AVISO, API Gmail, reautorizar token
  Cloud SQL no conecta -> IP autorizada + .env


--------------------------------------------------
NO SUBIR A GIT
--------------------------------------------------

  credenciales.json
  token.json
  .env
  CSV de corridas
  logs
