# CLONACION_CARPETA

Clona carpetas de Google Drive segun un Excel de rutas,
genera inventario, lo publica en Google Sheets
y envia un correo de aviso.

Ver tambien:
  ../README.md
  ../ARCHIVOS.md


--------------------------------------------------
FLUJO OPERATIVO (USO NORMAL)
--------------------------------------------------

Solo lanzas UN script. Al terminar, encadena lo demas:

  python clone_carpeta_drive.py
          |
          |-- 1. Lee RUTAS.xlsx
          |-- 2. Clona origen -> destino (reanudable)
          |-- 3. reporte_inventario_clon.py      -> Excel local
          |-- 4. publicar_inventario_sheets.py   -> Google Sheet
          |-- 5. notificar_clonacion.py          -> correo Gmail


--------------------------------------------------
CORREO AL CLONAR
--------------------------------------------------

Si forma parte del diseno.
Destinatarios: CORREOS_AVISO en .env
Contenido: estado + enlace a la Google Sheet
Si Sheets falla: adjunta el Excel


--------------------------------------------------
SCRIPTS
--------------------------------------------------

  clone_carpeta_drive.py         ENTRADA (clona + dispara 3-5)
  reporte_inventario_clon.py     Inventario Excel
  publicar_inventario_sheets.py  Sheet fija + compartir
  notificar_clonacion.py         Correo Gmail
  renovar_token.py               Regenera token.json
  comparar_clon_drive.py         Diagnostico (NO es flujo diario)

Todos los .py tienen comentarios tutorial en el codigo.


--------------------------------------------------
EXCEL DE RUTAS
--------------------------------------------------

Ruta por defecto en el codigo (ajustar si cambias de PC):

  C:\Users\angie_vera\Downloads\RUTAS.xlsx

Formatos aceptados:
  etiqueta | origen | destino
  cliente | etiqueta | origen | destino


--------------------------------------------------
CONFIGURACION
--------------------------------------------------

  1. Copia .env.example -> .env y define CORREOS_AVISO
  2. Coloca credentials.json (OAuth Desktop)
  3. Si falta token o permiso Gmail/Sheets:
       python renovar_token.py
  4. pip install -r requirements.txt


--------------------------------------------------
COMANDO PRINCIPAL
--------------------------------------------------

  cd CLONACION_CARPETA
  python clone_carpeta_drive.py


--------------------------------------------------
INVENTARIO
--------------------------------------------------

Es un REPORTE (Excel local = Google Sheet), no una carpeta de materiales.
Cuenta por tipo de carpeta; Moodle 01_... SI cuenta.
No requiere prefijo G.


--------------------------------------------------
RELACION CON GCP
--------------------------------------------------

Este bloque NO carga Cloud SQL.
Siguiente bloque: LMS_Fabrica


--------------------------------------------------
NO SUBIR A GIT
--------------------------------------------------

  credentials.json
  token.json
  .env
  clonacion.log
  hoja_inventario_id.txt
  reportes generados
