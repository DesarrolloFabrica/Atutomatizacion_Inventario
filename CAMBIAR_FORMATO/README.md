# CAMBIAR_FORMATO

Convierte imágenes JPG/JPEG a PNG en una carpeta de Google Drive y sus
subcarpetas. Corresponde al primer paso del flujo operativo, antes de la clonación.

## Requisitos

- Python 3.10 o superior
- Dependencias: `pip install -r requirements.txt`
- Credenciales OAuth de Google en esta carpeta:
  - `credenciales.json`
  - `token.json` (se genera en la primera autorización)
- La cuenta asociada al token debe tener acceso a la carpeta de Drive indicada

Los archivos `credenciales.json`, `token.json` y `.env` no forman parte del
repositorio.

## Parámetro de carpeta

En cada ejecución se especifica la carpeta de Drive con `--carpeta`:

- enlace de la carpeta, o
- identificador (segmento posterior a `/folders/` en el enlace)

Ejemplo de enlace:

```text
https://drive.google.com/drive/folders/<ID_CARPETA>
```

## Ejecución

```powershell
cd CAMBIAR_FORMATO
python convertir_jpg_a_png.py --carpeta "https://drive.google.com/drive/folders/<ID_CARPETA>"
```

```powershell
python convertir_jpg_a_png.py --carpeta <ID_CARPETA>
```

Desde el orquestador del repositorio:

```powershell
python run_flujo.py --excel "<RUTA>\RUTAS.xlsx" --carpeta-formato "https://drive.google.com/drive/folders/<ID_CARPETA>"
```

Si el material ya se encuentra en PNG, este paso puede omitirse con `--sin-formato`.

## Comportamiento

- Localiza archivos JPG/JPEG en la carpeta indicada y subcarpetas
- Genera el equivalente PNG en la misma ubicación
- Envía el JPG original a la papelera de Drive

Un resultado `Archivos convertidos: 0` con `Errores: 0` indica acceso correcto
sin archivos JPG presentes en la carpeta.

## Contenido del directorio

| Archivo | Descripción |
|---|---|
| `convertir_jpg_a_png.py` | Script de ejecución |
| `requirements.txt` | Dependencias |
| `codigo.js` / `codigos.txt` | Alternativa Apps Script (fuera del flujo diario) |

## Alcance

Este módulo no lee `RUTAS.xlsx`, no envía correo y no escribe en Cloud SQL.
