# CLONACION_CARPETA

Clona carpetas de Google Drive según un Excel de rutas, genera un **reporte de
inventario**, lo publica en Google Sheets y envía el **correo 1**.

## Primera vez (configuración)

1. Instalar dependencias:

```powershell
cd CLONACION_CARPETA
pip install -r requirements.txt
```

2. Copiar `.env.example` → `.env` y completar al menos:
   - `CORREOS_AVISO` — destinatarios del correo (separados por coma)

3. Colocar en esta carpeta (no van a Git):
   - `credentials.json` — OAuth Desktop
   - `token.json` — se crea al autorizar; si falta o caduca:

```powershell
python renovar_token.py
```

4. Tener el Excel `RUTAS.xlsx` con columnas:
   `cliente | etiqueta | origen | destino`
   (detalle en `../DICCIONARIO_DATOS_EXCEL.md`)

## Cómo indicar el Excel

No hay ruta de usuario fija en el código. Opciones:

```powershell
python clone_carpeta_drive.py --excel "C:\ruta\RUTAS.xlsx"
```

O variable de entorno:

```powershell
$env:RUTAS_XLSX="C:\ruta\RUTAS.xlsx"
python clone_carpeta_drive.py
```

También se busca `RUTAS.xlsx` en la raíz del repo o en la carpeta actual.

## Uso normal (un solo comando)

```powershell
cd CLONACION_CARPETA
python clone_carpeta_drive.py --excel "C:\ruta\RUTAS.xlsx"
```

Ese comando hace, en orden:

1. Lee el Excel  
2. Clona origen → destino en Drive  
3. Genera el inventario local: `reporte_inventario_clon.xlsx`  
4. Publica / actualiza la Google Sheet  
5. Envía el correo 1 con el link de la Sheet  

## Qué es el inventario

Es un **reporte de control** (no es material del curso):

- Compara origen vs destino (conteos, Moodle, faltantes, etc.)
- Sale en Excel local y en Google Sheet
- El correo 1 solo lleva el link de esa Sheet

## Scripts

| Script | Rol |
|---|---|
| `clone_carpeta_drive.py` | Entrada diaria (clona + encadena el resto) |
| `reporte_inventario_clon.py` | Arma el Excel de inventario |
| `publicar_inventario_sheets.py` | Publica en Google Sheets |
| `notificar_clonacion.py` | Correo 1 |
| `renovar_token.py` | Regenera `token.json` |
| `comparar_clon_drive.py` | Diagnóstico manual (NO diario) |

Diagnóstico manual (si lo necesitas):

```powershell
python comparar_clon_drive.py --origen "ENLACE_O_ID" --destino "ENLACE_O_ID"
```

## Relación con el resto del flujo

Este bloque **no** carga Cloud SQL.  
Siguiente bloque: `LMS_Fabrica`.

## No subir a Git

`credentials.json`, `token.json`, `.env`, `clonacion.log`, reportes generados.
