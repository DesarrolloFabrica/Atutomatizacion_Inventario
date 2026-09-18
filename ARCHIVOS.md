# Inventario de archivos del repositorio

Lista de lo que hay en el repo y para qué sirve.


==================================================
RAIZ
==================================================

  README.md                  -> vision general del flujo
  DOCUMENTACION_PROCESO.md   -> workflow + paso a paso diario
  DICCIONARIO_DATOS_EXCEL.md -> columnas de RUTAS.xlsx
  CHECKLIST_ENTREGA.md       -> validacion al cerrar el lote
  run_flujo.py               -> orquestador (formato -> clon -> CSV -> GCP)
  rutas_excel.py             -> localiza RUTAS.xlsx (--excel o RUTAS_XLSX)
  ARCHIVOS.md                -> este listado
  .gitignore                 -> evita subir secretos y basura de corridas
  .env.example               -> plantilla CORREOS_AVISO + DB_* (copiar a .env)


==================================================
CAMBIAR_FORMATO/   (JPG -> PNG, obligatorio en flujo diario)
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

  cargar_base_gcp.py            PASO 2 DIARIO
                                CSV -> Cloud SQL + dispara correo

  notificar_carga_lms.py        ENCADENADO
                                Correo Gmail con resumen + query SQL

  generar_base_lms.py           LIBRERIA (API publica)
                                Auth, parsers, columnas CSV, IDs

  lms_lib/                      Constantes compartidas

  clonar_esquema_pruebas.py     NO DIARIO (admin, una sola vez)

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
RUTAS Y METADATA
==================================================

Origen, destino y cliente se toman de RUTAS.xlsx.


==================================================
CORREOS (HAY DOS)
==================================================

  Despues del clon  -> notificar_clonacion.py  -> link Google Sheet
  Despues de GCP    -> notificar_carga_lms.py  -> resumen + query SQL


==================================================
ORDEN DE COMANDOS
==================================================

  python run_flujo.py --carpeta-formato "https://drive.google.com/drive/folders/TU_ID"

  # Bloques sueltos:
  cd CAMBIAR_FORMATO
  python convertir_jpg_a_png.py --carpeta "https://drive.google.com/drive/folders/TU_ID"

  cd ..\CLONACION_CARPETA
  python clone_carpeta_drive.py

  cd ..\LMS_Fabrica
  python generar_base_rutas.py --excel RUTAS.xlsx -o lms_base_rutas.csv
  python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas


Detalle: DOCUMENTACION_PROCESO.md
Cierre: CHECKLIST_ENTREGA.md
