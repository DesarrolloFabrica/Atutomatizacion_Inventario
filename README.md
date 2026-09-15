# Flujo LMS: formato, clonacion e inventario, carga a GCP

Herramientas en Python para fabrica de contenido (CUN).
Preparan material en Google Drive, lo clonan con control de calidad
y lo registran en Cloud SQL (planner_db).

Este repo NO incluye secretos. Cada persona configura OAuth y .env en su PC.


--------------------------------------------------
DOCUMENTACION POR CARPETA
--------------------------------------------------

  CAMBIAR_FORMATO/README.md     -> JPG a PNG
  CLONACION_CARPETA/README.md   -> clon + inventario + correo
  LMS_Fabrica/README.md         -> CSV + Cloud SQL + correo
  ARCHIVOS.md                   -> lista de cada archivo del repo


--------------------------------------------------
FLUJO COMPLETO (ORDEN)
--------------------------------------------------

  0. (Opcional) JPG -> PNG
  1. Clonar origen -> destino en Drive
  2. Inventario + Google Sheets + correo Gmail
  3. Escanear destino -> CSV
  4. Cargar CSV -> Cloud SQL + correo Gmail

No corre todo junto ni en paralelo.
Son bloques en serie. Cada bloque se lanza con su comando.


--------------------------------------------------
QUE HACE CADA BLOQUE
--------------------------------------------------

1) CAMBIAR_FORMATO (opcional)
   - Convierte JPG/JPEG a PNG en Drive.
   - El JPG va a la papelera.
   - Comando: python convertir_jpg_a_png.py

2) CLONACION_CARPETA
   - Lee RUTAS.xlsx (etiqueta, origen, destino).
   - Copia el arbol origen -> destino (puede reanudar).
   - Arma inventario (Excel local + una Google Sheet).
   - Envia correo Gmail con el link de esa Sheet.
   - Comando unico: python clone_carpeta_drive.py
     (al terminar el mismo script llama inventario, Sheets y correo)

3) LMS_Fabrica
   - Escanea solo la columna DESTINO del Excel.
   - Genera un CSV (puente para revisar).
   - Carga a Cloud SQL (por defecto fabrica_pruebas).
   - Envia otro correo Gmail con resumen y query SQL.
   - Comandos:
       python generar_base_rutas.py --excel RUTAS.xlsx -o lms_base_rutas.csv
       python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas


--------------------------------------------------
EXCEL RUTAS.xlsx
--------------------------------------------------

Una fila = un lote a procesar.

  etiqueta  = apodo humano (ej. prueba_angie). No se guarda en GCP.
  origen    = carpeta Drive a copiar (en carga GCP solo es referencia).
  destino   = carpeta Drive destino. En carga GCP es la UNICA que se escanea.
  cliente   = PRODUCTO, TANIA o LMS_correcciones (para clasificar en GCP).

El nombre del PROGRAMA en la base sale del nombre de la carpeta en Drive,
no de la etiqueta.


--------------------------------------------------
METADATA_EXTRA (importante)
--------------------------------------------------

En generar_base_rutas.py hay un diccionario largo con muchos programas.

Eso NO es la lista de lo que se va a escanear.
Es una libreta de apoyo (escuela / cliente por defecto).

Lo que se procesa sale SOLO de las filas de RUTAS.xlsx.
Si el Excel tiene 1 fila, solo se trabaja esa carpeta.


--------------------------------------------------
DOS REGLAS DISTINTAS
--------------------------------------------------

Inventario del clon (Drive):
  - Cuenta por tipo de carpeta (Moodle, contenidos, SCORM, PDF, etc.).
  - Archivos tipo 01_Quiz.txt en ACTIVIDADES MOODLE SI cuentan.

Carga a GCP (LMS_Fabrica):
  - Solo indexa archivos que empiezan con G + digitos (ej. G1001_intro.pdf).
  - El resto puede estar en Drive, pero no entra al CSV ni a la base.


--------------------------------------------------
CORREOS (HAY DOS)
--------------------------------------------------

Despues del clon:
  - Script: notificar_clonacion.py
  - Lleva el link de la Google Sheet del inventario.

Despues de cargar GCP:
  - Script: notificar_carga_lms.py
  - Lleva resumen + query SQL para validar.

Ninguno se dispara solo por subir un PDF a Drive.
Destinatarios: CORREOS_AVISO en el archivo .env


--------------------------------------------------
CREDENCIALES (NO SUBIR A GIT)
--------------------------------------------------

  credentials.json / credenciales.json  = OAuth Desktop de Google
  token.json                            = sesion despues de autorizar
  .env                                  = correos + datos de la base

Plantillas:
  CLONACION_CARPETA/.env.example
  LMS_Fabrica/.env.example

Hay un .gitignore en la raiz para no subir secretos.


--------------------------------------------------
REQUISITOS
--------------------------------------------------

  - Python 3.10 o superior
  - pip install -r requirements.txt (en cada carpeta que uses)
  - Acceso a las carpetas de Drive del lote
  - Para GCP: IP autorizada en Cloud SQL y .env completo


--------------------------------------------------
QUE NO ES FLUJO DIARIO
--------------------------------------------------

  - Crear el esquema fabrica_pruebas (se hace UNA vez).
  - clonar_esquema_pruebas.py (solo administracion excepcional).
  - comparar_clon_drive.py (diagnostico manual opcional).
  - codigo.js / codigos.txt (respaldo Apps Script; el oficial es Python).


--------------------------------------------------
ESTRUCTURA DEL REPO
--------------------------------------------------

  FlujoFormato_clonacion/
  |-- README.md
  |-- ARCHIVOS.md
  |-- .gitignore
  |-- CAMBIAR_FORMATO/
  |-- CLONACION_CARPETA/
  |-- LMS_Fabrica/


--------------------------------------------------
PARA ANALISTAS (UNA FRASE)
--------------------------------------------------

Primero aseguras una copia limpia en Drive y un inventario compartido
por correo; despues traduces esa carpeta destino a un CSV y la registras
en la base de prueba, con otro correo para validar.


--------------------------------------------------
COMANDOS RAPIDOS
--------------------------------------------------

  cd CAMBIAR_FORMATO
  python convertir_jpg_a_png.py

  cd ..\CLONACION_CARPETA
  python clone_carpeta_drive.py

  cd ..\LMS_Fabrica
  python generar_base_rutas.py --excel RUTAS.xlsx -o lms_base_rutas.csv
  python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas


Documentacion del flujo operativo LMS - septiembre 2026.
