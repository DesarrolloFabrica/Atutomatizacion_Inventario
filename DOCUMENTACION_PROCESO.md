# Documentación del proceso — Flujo Automatizacion Inventario

Guía operativa para que cualquiera del equipo pueda ejecutar el flujo sin dudas.

También ver: `README.md`, `DICCIONARIO_DATOS_EXCEL.md`, `CHECKLIST_ENTREGA.md`
y el README de cada carpeta.


==================================================
1. QUÉ HACE ESTE FLUJO
==================================================

1. Convierte JPG → PNG en Drive  
2. Clona origen → destino, genera inventario (reporte) y envía correo 1  
3. Registra el destino en Cloud SQL y envía correo 2  


==================================================
2. ANTES DE EMPEZAR (UNA VEZ POR PC)
==================================================

1. Clonar / descargar este repositorio.
2. Instalar Python 3.10+ y dependencias de cada bloque (`pip install -r requirements.txt`).
3. Pedir al equipo (no están en Git):
   - `credentials.json` / `credenciales.json` (OAuth Desktop)
   - valores de `.env` (correos y, si aplica, base de datos)
4. Crear `.env` desde `.env.example` (raíz o en cada bloque).
5. Autorizar Google la primera vez (se crea `token.json`).
6. Tener el Excel `RUTAS.xlsx` (columnas: cliente, etiqueta, origen, destino).

La cuenta de Google del token debe tener acceso a las carpetas de Drive del lote.


==================================================
3. WORKFLOW COMPLETO
==================================================

```text
1) CAMBIAR_FORMATO  (obligatorio)
    JPG/JPEG -> PNG en Drive
    Indicar carpeta con --carpeta / --carpeta-formato (enlace o ID)
              |
              v
2) CLONACION_CARPETA
    Lee RUTAS.xlsx (--excel o variable RUTAS_XLSX)
      -> clonar origen -> destino
      -> inventario = reporte Excel local + Google Sheet
      -> CORREO 1 (link de la Sheet)
              |
              v
3) LMS_Fabrica
    Lee el mismo Excel (columna destino)
      -> CSV
      -> Cloud SQL (fabrica_pruebas)
      -> CORREO 2
```

**Inventario** = reporte de control del clon (no es el CSV de GCP).  
Orden interno del clon: **clonar → inventario → Sheet → correo**.


==================================================
4. CÓMO EJECUTAR
==================================================

### Opción A — Todo seguido (recomendado)

Desde la raíz del repo:

```powershell
python run_flujo.py --excel "C:\ruta\RUTAS.xlsx" --carpeta-formato "https://drive.google.com/drive/folders/TU_ID"
```

Opciones útiles:

| Opción | Significado |
|---|---|
| `--excel` | Ruta a `RUTAS.xlsx` |
| `--carpeta-formato` | Enlace o ID de carpeta para JPG→PNG |
| `--sin-formato` | Omite JPG→PNG (solo si el lote ya está en PNG) |
| `--sin-clon` | Omite clonación |
| `--sin-gcp` | Omite CSV y Cloud SQL |
| `--sin-correo` | No envía el correo 2 |

### Opción B — Por bloques

Detalle y “primera vez” en:

- `CAMBIAR_FORMATO/README.md`
- `CLONACION_CARPETA/README.md`
- `LMS_Fabrica/README.md`


==================================================
5. REGLAS IMPORTANTES
==================================================

1. En GCP solo se escanea la columna **destino** del Excel.
2. Hay **dos correos** distintos (Sheet del clon y resumen SQL).
3. Esquema diario: `fabrica_pruebas`.
4. `clonar_esquema_pruebas.py` **no** es flujo diario (admin, una vez).
5. No versionar secretos (`.env`, tokens, credenciales).
6. Clientes: `PRODUCTO`, `TANIA`, `LMS_correcciones` (en GCP correcciones → PRODUCTO).
7. Indexación: si hay `G`+números se usa; si no, el nombre del archivo sin extensión.


==================================================
6. PROBLEMAS FRECUENTES
==================================================

| Síntoma | Qué revisar |
|---|---|
| No lee el Excel | Cerrar `RUTAS.xlsx`; pasar `--excel` o `RUTAS_XLSX` |
| File not found (Drive) | La cuenta del `token.json` no tiene acceso a esa carpeta |
| No llega correo | `CORREOS_AVISO`, scopes Gmail, `renovar_token.py` |
| CSV vacío | Estructura de carpetas, permisos, columna destino |
| Cloud SQL no conecta | IP autorizada + `.env` con `DB_*` |
| Formato convierte 0 | Carpeta vacía o sin JPG (si Errores: 0, el acceso sí funcionó) |


==================================================
7. CIERRE DE LOTE
==================================================

Completar `CHECKLIST_ENTREGA.md`.
