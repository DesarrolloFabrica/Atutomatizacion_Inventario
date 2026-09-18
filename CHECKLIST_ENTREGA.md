# Checklist de entrega — Flujo Automatizacion Inventario

Usa esta lista **al final de cada corrida** (o antes de dar por cerrado un lote)
para confirmar que el proceso quedó bien.

Marca cada ítem con `[x]` cuando esté OK.


--------------------------------------------------
A. PREPARACIÓN (antes de correr)
--------------------------------------------------

- [ ] `RUTAS.xlsx` lleno con columnas correctas (`cliente`, `etiqueta`, `origen`, `destino`)
- [ ] Excel **guardado y cerrado**
- [ ] URLs/IDs de origen y destino válidos (carpetas Drive accesibles)
- [ ] Valores de `cliente` válidos: `PRODUCTO`, `TANIA` o `LMS_correcciones`
- [ ] Credenciales locales listas (`credentials.json` / `credenciales.json` + `token.json`)
- [ ] `.env` con `CORREOS_AVISO` (y `DB_*` si vas a cargar GCP)
- [ ] Dependencias instaladas (`pip install -r requirements.txt` en cada bloque que uses)


--------------------------------------------------
B. EJECUCIÓN (elige una)
--------------------------------------------------

Opción continua (recomendado):

- [ ] Se ejecutó: `python run_flujo.py --carpeta-formato "https://drive.google.com/drive/folders/TU_ID"` (o `--sin-formato` si el lote ya está en PNG)
- [ ] El orquestador terminó con "FLUJO COMPLETO: OK"

Opción por bloques: continuar con C–D abajo.


--------------------------------------------------
C. FORMATO JPG → PNG (obligatorio en flujo diario)
--------------------------------------------------

- [ ] Se indicó la carpeta de Drive con `--carpeta` / `--carpeta-formato` (enlace o ID)
- [ ] Script terminó sin error
- [ ] En Drive ya no quedan JPG del lote (quedaron PNG)


--------------------------------------------------
D. CLONACIÓN + INVENTARIO + CORREO 1 (si corriste por bloques)
--------------------------------------------------

- [ ] Se ejecutó: `python clone_carpeta_drive.py`
- [ ] Clonación terminó sin error (origen → destino)
- [ ] Se generó inventario local (Excel de reporte)
- [ ] Se actualizó / publicó la Google Sheet de inventario
- [ ] Llegó el **correo 1** con el link de la Sheet
- [ ] Conteos origen vs destino coherentes (sin faltantes graves)


--------------------------------------------------
E. CARGA LMS / GCP + CORREO 2 (si corriste por bloques)
--------------------------------------------------

- [ ] Se generó CSV: `python generar_base_rutas.py --excel RUTAS.xlsx -o lms_base_rutas.csv`
- [ ] El CSV tiene filas (no quedó vacío)
- [ ] Se cargó a prueba: `python cargar_base_gcp.py -i lms_base_rutas.csv --schema fabrica_pruebas`
- [ ] Llegó el **correo 2** (resumen + query SQL)
- [ ] Query del correo abre resultados esperados en Cloud SQL Studio
- [ ] Cliente / raíz del lote se ven correctos (`LMS_correcciones` → raíz LMS_Carga)


--------------------------------------------------
F. LO QUE NO DEBE ESTAR EN LA ENTREGA DIARIA
--------------------------------------------------

- [ ] **No** se corrió `clonar_esquema_pruebas.py` (eso es admin, una sola vez)
- [ ] **No** se usó `--schema fabrica` salvo pedido explícito del equipo
- [ ] **No** se subieron a Git: `.env`, `token.json`, credenciales, CSV/Excel de corrida


--------------------------------------------------
G. CIERRE / ENTREGA
--------------------------------------------------

- [ ] Documentación revisada si hubo cambios de proceso
- [ ] Lote marcado como entregado / comunicado al equipo

---

## Resultado rápido

| Bloque | OK | Observación |
|---|---|---|
| Preparación | | |
| Ejecución continua / bloques | | |
| Formato (si aplica) | | |
| Clonación + correo 1 | | |
| GCP + correo 2 | | |
| Cierre | | |

**Fecha:** _______________  
**Lote / etiqueta:** _______________  
**Responsable:** _______________  
