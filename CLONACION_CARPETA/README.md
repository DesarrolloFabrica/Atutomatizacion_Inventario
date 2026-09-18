# CLONACION_CARPETA

Clona carpetas de Google Drive a partir de un archivo de rutas, genera el
reporte de inventario, lo publica en Google Sheets y envía la notificación
asociada (correo 1).

## Requisitos

- Python 3.10 o superior
- Dependencias: `pip install -r requirements.txt`
- Archivo `.env` (a partir de `.env.example`) con `CORREOS_AVISO`
- Credenciales OAuth en esta carpeta:
  - `credentials.json`
  - `token.json`
- Archivo `RUTAS.xlsx` con columnas: `cliente | etiqueta | origen | destino`

Para regenerar el token:

```powershell
python renovar_token.py
```

Los archivos `credentials.json`, `token.json` y `.env` no forman parte del
repositorio. El diccionario de columnas del Excel está en
`../DICCIONARIO_DATOS_EXCEL.md`.

## Ubicación de RUTAS.xlsx

El Excel se indica en cada ejecución. Alternativas válidas:

```powershell
python clone_carpeta_drive.py --excel "<RUTA>\RUTAS.xlsx"
```

```powershell
$env:RUTAS_XLSX="<RUTA>\RUTAS.xlsx"
python clone_carpeta_drive.py
```

Si no se especifica, se busca `RUTAS.xlsx` en la raíz del repositorio o en el
directorio de trabajo actual.

## Ejecución

```powershell
cd CLONACION_CARPETA
python clone_carpeta_drive.py --excel "<RUTA>\RUTAS.xlsx"
```

Secuencia automática:

1. Lectura del Excel  
2. Clonación origen → destino en Drive  
3. Generación del inventario local (`reporte_inventario_clon.xlsx`)  
4. Publicación en Google Sheets  
5. Envío del correo 1 con el enlace de la hoja  

## Inventario

El inventario es un reporte de control de la clonación (conteos, materiales,
faltantes). Se materializa como Excel local y como Google Sheet. No constituye
el CSV de carga a Cloud SQL.

## Scripts

| Script | Función |
|---|---|
| `clone_carpeta_drive.py` | Entrada del bloque (clona y encadena el resto) |
| `reporte_inventario_clon.py` | Genera el Excel de inventario |
| `publicar_inventario_sheets.py` | Publica en Google Sheets |
| `notificar_clonacion.py` | Correo 1 |
| `renovar_token.py` | Regeneración de `token.json` |
| `comparar_clon_drive.py` | Diagnóstico manual (fuera del flujo diario) |

```powershell
python comparar_clon_drive.py --origen "<ENLACE_O_ID>" --destino "<ENLACE_O_ID>"
```

Siguiente módulo del flujo: `LMS_Fabrica`.
