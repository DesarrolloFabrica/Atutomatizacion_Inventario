# Inventario de archivos del repositorio

Listado de componentes del proyecto Automatización Inventario.


==================================================
RAÍZ
==================================================

  README.md                  Visión general
  DOCUMENTACION_PROCESO.md   Secuencia operativa
  DICCIONARIO_DATOS_EXCEL.md Columnas de RUTAS.xlsx
  CHECKLIST_ENTREGA.md       Verificación de cierre
  run_flujo.py               Orquestador del flujo
  rutas_excel.py             Resolución de RUTAS.xlsx
  ARCHIVOS.md                Este listado
  .gitignore                 Exclusión de secretos y artefactos
  .env.example               Plantilla de variables de entorno


==================================================
CAMBIAR_FORMATO/
==================================================

  convertir_jpg_a_png.py     Conversión JPG/JPEG → PNG en Drive
  codigo.js                  Alternativa Apps Script
  codigos.txt                Copia de texto del Apps Script
  requirements.txt           Dependencias
  README.md                  Documentación del módulo

  Excluidos del repositorio: credenciales.json, token.json


==================================================
CLONACION_CARPETA/
==================================================

  clone_carpeta_drive.py         Entrada del bloque (clonación + encadenamiento)
  reporte_inventario_clon.py     Reporte de inventario
  publicar_inventario_sheets.py  Publicación en Google Sheets
  notificar_clonacion.py         Correo 1
  renovar_token.py               Regeneración de token.json
  comparar_clon_drive.py         Diagnóstico (fuera del flujo diario)
  .env.example                   Plantilla
  requirements.txt / README.md

  Excluidos del repositorio: credentials.json, token.json, .env,
  hoja_inventario_id.txt, clonacion.log, reportes generados


==================================================
LMS_Fabrica/
==================================================

  generar_base_rutas.py      Excel → CSV
  cargar_base_gcp.py         CSV → Cloud SQL + correo 2
  notificar_carga_lms.py     Notificación de carga
  generar_base_lms.py        Librería compartida
  lms_lib/                   Constantes compartidas
  clonar_esquema_pruebas.py  Administración de esquema (fuera del flujo diario)
  .env.example               Plantilla
  requirements.txt / README.md

  Excluidos del repositorio: credenciales.json, token.json, .env, CSV de corrida


==================================================
ENTRADAS DEL FLUJO
==================================================

Origen, destino y cliente se toman de RUTAS.xlsx.
La carpeta de conversión JPG→PNG se indica con --carpeta / --carpeta-formato.


==================================================
NOTIFICACIONES
==================================================

  Tras la clonación  -> notificar_clonacion.py  -> enlace Google Sheet
  Tras la carga GCP  -> notificar_carga_lms.py  -> resumen + consulta SQL


==================================================
EJECUCIÓN
==================================================

  python run_flujo.py --excel "<RUTA>\RUTAS.xlsx" --carpeta-formato "https://drive.google.com/drive/folders/<ID_CARPETA>"

  cd CAMBIAR_FORMATO
  python convertir_jpg_a_png.py --carpeta "https://drive.google.com/drive/folders/<ID_CARPETA>"

  cd CLONACION_CARPETA
  python clone_carpeta_drive.py --excel "<RUTA>\RUTAS.xlsx"

  cd LMS_Fabrica
  python generar_base_rutas.py --excel "<RUTA>\RUTAS.xlsx" -o lms_base_rutas.csv
  python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas

Documentación operativa: DOCUMENTACION_PROCESO.md
Validación de entrega: CHECKLIST_ENTREGA.md
