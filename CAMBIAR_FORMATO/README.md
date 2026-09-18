# CAMBIAR_FORMATO

Convierte imágenes JPG/JPEG a PNG dentro de una carpeta de Google Drive
(incluye subcarpetas). Es el primer paso del flujo diario, antes de clonar.

## Qué debes indicar

En cada ejecución se indica **qué carpeta de Drive** se va a procesar, con
`--carpeta`. Puedes usar:

- el **enlace** de la carpeta (el que copias desde el navegador), o
- el **ID** de la carpeta (la parte final del enlace, después de `/folders/`).

Ejemplo de enlace:

`https://drive.google.com/drive/folders/TU_ID_DE_CARPETA`

Ahí el ID es la parte final: `TU_ID_DE_CARPETA`

## Uso

```powershell
cd CAMBIAR_FORMATO
pip install -r requirements.txt
python convertir_jpg_a_png.py --carpeta "https://drive.google.com/drive/folders/TU_ID"
```

O solo con el ID:

```powershell
python convertir_jpg_a_png.py --carpeta TU_ID
```

En el flujo completo:

```powershell
python run_flujo.py --carpeta-formato "https://drive.google.com/drive/folders/TU_ID"
```

Si el lote ya está en PNG, puedes omitir este paso con `--sin-formato`.

## Archivos

- `convertir_jpg_a_png.py` — script oficial
- `codigo.js` / `codigos.txt` — respaldo Apps Script
- `requirements.txt`

Credenciales locales (no van a Git): `credenciales.json`, `token.json`.

## Notas

- No lee `RUTAS.xlsx`, no envía correo y no escribe en Cloud SQL.
- El JPG original pasa a la papelera de Drive; el PNG queda en la misma carpeta.
