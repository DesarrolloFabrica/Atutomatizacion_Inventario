# Documentación del proceso — Automatización Inventario

Documentación operativa del flujo de preparación, clonación e indexación de
materiales en Google Drive y Cloud SQL.


==================================================
1. OBJETIVO
==================================================

El flujo:

1. Convierte JPG/JPEG a PNG en Drive  
2. Clona carpetas origen → destino, genera el reporte de inventario y envía el correo 1  
3. Registra el destino en Cloud SQL y envía el correo 2  


==================================================
2. REQUISITOS DE ENTORNO
==================================================

- Python 3.10 o superior  
- Dependencias de cada módulo (`pip install -r requirements.txt`)  
- Credenciales OAuth de Google (`credentials.json` / `credenciales.json` y `token.json`)  
- Archivo `.env` a partir de `.env.example` (correos y, para carga, parámetros de base de datos)  
- Archivo `RUTAS.xlsx` con las columnas definidas en `DICCIONARIO_DATOS_EXCEL.md`  
- Acceso a las carpetas de Drive del lote y, para carga, IP autorizada en Cloud SQL  

Los secretos y archivos de corrida no se versionan en el repositorio.


==================================================
3. SECUENCIA DEL PROCESO
==================================================

```text
1) CAMBIAR_FORMATO
    JPG/JPEG -> PNG
    Parámetro: --carpeta / --carpeta-formato (enlace o ID de carpeta Drive)
              |
              v
2) CLONACION_CARPETA
    Entrada: RUTAS.xlsx (--excel o variable RUTAS_XLSX)
      -> clonación origen -> destino
      -> inventario (reporte Excel + Google Sheet)
      -> correo 1
              |
              v
3) LMS_Fabrica
    Entrada: RUTAS.xlsx (columna destino)
      -> CSV
      -> Cloud SQL (fabrica_pruebas)
      -> correo 2
```

El inventario es el reporte de control de la clonación.  
No corresponde al CSV de carga hacia Cloud SQL.

Orden interno del bloque de clonación: clonación → inventario → Sheet → correo 1.


==================================================
4. EJECUCIÓN
==================================================

### Flujo completo

```powershell
python run_flujo.py --excel "<RUTA>\RUTAS.xlsx" --carpeta-formato "https://drive.google.com/drive/folders/<ID_CARPETA>"
```

| Parámetro | Descripción |
|---|---|
| `--excel` | Ruta a `RUTAS.xlsx` |
| `--carpeta-formato` | Enlace o ID de carpeta para conversión JPG→PNG |
| `--sin-formato` | Omite la conversión de formato |
| `--sin-clon` | Omite la clonación |
| `--sin-gcp` | Omite generación de CSV y carga a Cloud SQL |
| `--sin-correo` | Omite el correo 2 |

### Ejecución por módulos

Ver la documentación de cada directorio:

- `CAMBIAR_FORMATO/README.md`
- `CLONACION_CARPETA/README.md`
- `LMS_Fabrica/README.md`


==================================================
5. REGLAS OPERATIVAS
==================================================

1. La carga a Cloud SQL utiliza únicamente la columna **destino** del Excel.  
2. Existen dos notificaciones independientes (correo 1 y correo 2).  
3. El esquema diario es `fabrica_pruebas`.  
4. `clonar_esquema_pruebas.py` no forma parte del flujo diario.  
5. No versionar secretos ni artefactos de corrida.  
6. Valores de cliente admitidos: `PRODUCTO`, `TANIA`, `LMS_correcciones`  
   (`LMS_correcciones` se registra en GCP como cliente PRODUCTO y raíz LMS_Carga).  
7. Código de archivo: prefijo `G` + dígitos si existe; en su defecto, nombre sin extensión.


==================================================
6. INCIDENCIAS FRECUENTES
==================================================

| Situación | Verificación |
|---|---|
| Excel no leído | Archivo cerrado; parámetro `--excel` o variable `RUTAS_XLSX` |
| File not found (Drive) | Permisos de la cuenta asociada al `token.json` sobre la carpeta |
| Correo no recibido | `CORREOS_AVISO`, permisos Gmail, vigencia del token |
| CSV vacío | Estructura de carpetas, permisos, columna destino |
| Error de conexión a Cloud SQL | IP autorizada y variables `DB_*` en `.env` |
| Conversión con 0 archivos | Carpeta sin JPG; si `Errores: 0`, el acceso fue correcto |


==================================================
7. CIERRE
==================================================

Validación de entrega: `CHECKLIST_ENTREGA.md`.
