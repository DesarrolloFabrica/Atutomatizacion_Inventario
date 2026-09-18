# CAMBIAR_FORMATO

Convierte imágenes JPG/JPEG a PNG dentro de una carpeta de Google Drive
(incluye subcarpetas). Es el **primer paso** del flujo diario, antes de clonar.

## Primera vez (configuración)

1. Instalar dependencias:

```powershell
cd CAMBIAR_FORMATO
pip install -r requirements.txt
```

2. Colocar en esta carpeta (no van a Git; pedirlos al equipo si no los tienes):
   - `credenciales.json` — OAuth Desktop de Google
   - `token.json` — se crea al autorizar la primera vez (o cópialo desde `LMS_Fabrica/`)

3. La cuenta de Google del `token.json` debe tener **acceso** a la carpeta de Drive
   que vas a procesar. Si Drive responde “File not found”, es un tema de permisos
   o de cuenta, no del comando.

## Qué debes indicar en cada corrida

La carpeta se indica con `--carpeta`. Puedes usar:

- el **enlace** de la carpeta (copiado desde el navegador), o
- el **ID** (la parte final del enlace, después de `/folders/`).

Ejemplo:

```text
https://drive.google.com/drive/folders/TU_ID_DE_CARPETA
                                 └── este es el ID ─┘
```

## Uso

```powershell
cd CAMBIAR_FORMATO
python convertir_jpg_a_png.py --carpeta "https://drive.google.com/drive/folders/TU_ID"
```

Solo con el ID:

```powershell
python convertir_jpg_a_png.py --carpeta TU_ID
```

Desde el flujo completo (raíz del repo):

```powershell
python run_flujo.py --excel "RUTA\RUTAS.xlsx" --carpeta-formato "https://drive.google.com/drive/folders/TU_ID"
```

Si el lote **ya está en PNG**, puedes omitir este paso con `--sin-formato`.

## Qué hace el script

- Busca JPG/JPEG en la carpeta y subcarpetas
- Crea el PNG en el mismo lugar
- Envía el JPG original a la papelera de Drive

Si imprime `Archivos convertidos: 0` y `Errores: 0`, el acceso funcionó pero
**no había JPG** en esa carpeta (puede estar vacía o solo tener PNG).

## Archivos de esta carpeta

| Archivo | Uso |
|---|---|
| `convertir_jpg_a_png.py` | Script oficial |
| `requirements.txt` | Dependencias |
| `codigo.js` / `codigos.txt` | Respaldo Apps Script (no es el flujo diario) |

## Notas

- No lee `RUTAS.xlsx`, no envía correo y no escribe en Cloud SQL.
- No subir a Git: `credenciales.json`, `token.json`.
