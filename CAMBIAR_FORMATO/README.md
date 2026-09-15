# CAMBIAR_FORMATO

Convierte imagenes JPG/JPEG a PNG dentro de una carpeta de Google Drive
(y subcarpetas).

Ver tambien:
  ../README.md
  ../ARCHIVOS.md


--------------------------------------------------
CUANDO USARLO
--------------------------------------------------

Solo si el material tiene JPG que deban quedar en PNG antes de clonar.
No es obligatorio en cada corrida.


--------------------------------------------------
ARCHIVOS DE ESTA CARPETA
--------------------------------------------------

  convertir_jpg_a_png.py   Oficial (Python en la PC + API Drive)
  codigo.js                Misma logica en Google Apps Script
  codigos.txt              Copia en texto del JS (respaldo)
  requirements.txt         Dependencias (google-*, Pillow)
  README.md                Este documento

Secretos locales (NO Git):
  credenciales.json
  token.json


--------------------------------------------------
COMO FUNCIONA (convertir_jpg_a_png.py)
--------------------------------------------------

  1. Autentica con OAuth (credenciales.json -> token.json)
  2. Parte de ID_CARPETA definido en el script (ajustarlo al lote)
  3. Por cada JPEG: descarga -> Pillow -> sube PNG -> trash del JPG
  4. Recorre subcarpetas

El codigo esta comentado paso a paso dentro del .py


--------------------------------------------------
COMANDO
--------------------------------------------------

  cd CAMBIAR_FORMATO
  pip install -r requirements.txt
  python convertir_jpg_a_png.py


--------------------------------------------------
APPS SCRIPT (ALTERNATIVA)
--------------------------------------------------

Pegar codigo.js en Extensiones -> Apps Script de Drive,
cambiar idCarpeta, ejecutar convertirJPGaPNG.


--------------------------------------------------
NOTAS
--------------------------------------------------

  - No lee RUTAS.xlsx
  - No envia correo
  - No toca Cloud SQL
