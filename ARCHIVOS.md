# Inventario de archivos del repositorio

Lista de TODO lo que hay en FlujoFormato_clonacion y para que sirve.
Los scripts .py tienen comentarios tutorial dentro del codigo.


==================================================
RAIZ
==================================================

  README.md      -> vision general del flujo (este es el principal)
  ARCHIVOS.md    -> este inventario
  .gitignore     -> evita subir secretos y basura de corridas


==================================================
CAMBIAR_FORMATO/   (JPG -> PNG, opcional)
==================================================

  convertir_jpg_a_png.py   USO DIARIO SI APLICA
                           Script oficial Python: convierte JPG a PNG en Drive

  codigo.js                ALTERNATIVA
                           Misma logica en Google Apps Script (dentro de Drive)

  codigos.txt              RESPALDO
                           Copia en texto del JS

  requirements.txt         SETUP
                           Dependencias Python

  README.md                DOCS
                           Como usar este bloque

  Local (NO van a Git):
    credenciales.json
    token.json


==================================================
CLONACION_CARPETA/   (clon + inventario + correo)
==================================================

  clone_carpeta_drive.py        ENTRADA PRINCIPAL
                                Lee Excel, clona Drive, encadena inventario + Sheet + correo

  reporte_inventario_clon.py    ENCADENADO
                                Arma Excel de inventario (origen vs destino)

  publicar_inventario_sheets.py ENCADENADO
                                Sube/sobrescribe la Google Sheet fija

  notificar_clonacion.py        ENCADENADO
                                Correo Gmail con link de la Sheet

  renovar_token.py              MANTENIMIENTO
                                Regenera token.json (Drive + Sheets + Gmail)

  comparar_clon_drive.py        DIAGNOSTICO (no es flujo diario)
                                Compara dos IDs fijos de Drive

  .env.example                  PLANTILLA
                                Ejemplo de CORREOS_AVISO

  .gitignore / requirements.txt / README.md

  Local (NO van a Git):
    credentials.json
    token.json
    .env
    hoja_inventario_id.txt
    clonacion.log
    reportes generados


==================================================
LMS_Fabrica/   (CSV + Cloud SQL + correo)
==================================================

  generar_base_rutas.py         PASO 1 DIARIO
                                Excel -> escanea destino Drive -> CSV
                                (solo archivos G + digitos)

  cargar_base_gcp.py            PASO 2 DIARIO
                                CSV -> Cloud SQL + dispara correo

  notificar_carga_lms.py        ENCADENADO
                                Correo Gmail con resumen + query SQL

  generar_base_lms.py           LIBRERIA
                                Auth, parsers, columnas CSV, IDs
                                (la importan los otros scripts)

  clonar_esquema_pruebas.py     NO DIARIO
                                Copia esquema fabrica -> fabrica_pruebas
                                (se hace una vez / solo admin)

  .env.example                  PLANTILLA
                                CORREOS_AVISO + DB_* + LMS_SCHEMA

  .gitignore / requirements.txt / README.md

  Local (NO van a Git):
    credenciales.json
    token.json
    .env
    lms_base_rutas.csv (generado)
    otros CSV de corridas


==================================================
NOTA: METADATA_EXTRA
==================================================

En generar_base_rutas.py hay un diccionario largo de programas.

NO son rutas a ejecutar.
Es un catalogo de apoyo (escuela/cliente).
Lo que se procesa sale solo de RUTAS.xlsx.


==================================================
CORREOS (HAY DOS)
==================================================

  Despues del clon  -> notificar_clonacion.py  -> link Google Sheet
  Despues de GCP    -> notificar_carga_lms.py  -> resumen + query SQL

Ninguno se dispara solo por subir un PDF a Drive.


==================================================
ORDEN DE COMANDOS
==================================================

  cd CAMBIAR_FORMATO
  python convertir_jpg_a_png.py

  cd ..\CLONACION_CARPETA
  python clone_carpeta_drive.py

  cd ..\LMS_Fabrica
  python generar_base_rutas.py --excel RUTAS.xlsx -o lms_base_rutas.csv
  python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas
