# CAMBIAR_FORMATO

Convierte JPG/JPEG a PNG en una carpeta de Google Drive (y subcarpetas).
Paso **obligatorio** del flujo diario (antes del clon).

## Uso

```powershell
cd CAMBIAR_FORMATO
pip install -r requirements.txt
python convertir_jpg_a_png.py --carpeta <ID_o_URL_Drive>
```

`--carpeta` es obligatorio (ID o URL). No hay carpeta hardcodeada en el código.

## Archivos

- `convertir_jpg_a_png.py` — oficial
- `codigo.js` / `codigos.txt` — respaldo Apps Script
- `requirements.txt`

Secretos locales (NO Git): `credenciales.json`, `token.json`.

## Notas

- No lee `RUTAS.xlsx`, no envía correo, no toca Cloud SQL.
- En `run_flujo.py`: `--carpeta-formato` (o `--sin-formato` solo si el lote ya está en PNG).
