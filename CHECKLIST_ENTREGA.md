# Checklist de entrega — Automatización Inventario

Lista de verificación al cierre de cada corrida o lote.


--------------------------------------------------
A. PREPARACIÓN
--------------------------------------------------

- [ ] `RUTAS.xlsx` con columnas `cliente`, `etiqueta`, `origen`, `destino`
- [ ] Excel guardado y cerrado
- [ ] Enlaces o IDs de origen y destino válidos
- [ ] Valores de `cliente` válidos: `PRODUCTO`, `TANIA` o `LMS_correcciones`
- [ ] Credenciales OAuth disponibles (`credentials.json` / `credenciales.json` + `token.json`)
- [ ] `.env` con `CORREOS_AVISO` (y `DB_*` si corresponde carga a Cloud SQL)
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)


--------------------------------------------------
B. EJECUCIÓN
--------------------------------------------------

Flujo continuo:

- [ ] Ejecución de `python run_flujo.py --excel "<RUTA>\RUTAS.xlsx" --carpeta-formato "<ENLACE_O_ID>"`
- [ ] Finalización con mensaje `FLUJO COMPLETO: OK`

Ejecución por módulos: continuar con las secciones C a E.


--------------------------------------------------
C. CONVERSIÓN JPG → PNG
--------------------------------------------------

- [ ] Carpeta de Drive indicada con `--carpeta` / `--carpeta-formato`
- [ ] Ejecución sin error
- [ ] Material del lote disponible en PNG


--------------------------------------------------
D. CLONACIÓN + INVENTARIO + CORREO 1
--------------------------------------------------

- [ ] Ejecución de `python clone_carpeta_drive.py --excel "<RUTA>\RUTAS.xlsx"`
- [ ] Clonación origen → destino completada
- [ ] Inventario local generado (Excel de reporte)
- [ ] Google Sheet de inventario actualizada
- [ ] Correo 1 enviado con el enlace de la Sheet
- [ ] Conteos origen vs destino coherentes


--------------------------------------------------
E. CARGA LMS / GCP + CORREO 2
--------------------------------------------------

- [ ] CSV generado (`generar_base_rutas.py`)
- [ ] CSV con filas
- [ ] Carga a `fabrica_pruebas` completada
- [ ] Correo 2 enviado (resumen + consulta SQL)
- [ ] Resultados verificados en Cloud SQL Studio
- [ ] Cliente y raíz del lote correctos (`LMS_correcciones` → raíz LMS_Carga)


--------------------------------------------------
F. EXCLUSIONES DEL FLUJO DIARIO
--------------------------------------------------

- [ ] No se ejecutó `clonar_esquema_pruebas.py`
- [ ] No se utilizó `--schema fabrica` salvo autorización expresa
- [ ] No se versionaron secretos ni artefactos de corrida


--------------------------------------------------
G. CIERRE
--------------------------------------------------

- [ ] Documentación revisada si hubo cambios de proceso
- [ ] Lote registrado como entregado

---

## Registro

| Bloque | OK | Observación |
|---|---|---|
| Preparación | | |
| Ejecución | | |
| Formato | | |
| Clonación + correo 1 | | |
| GCP + correo 2 | | |
| Cierre | | |

**Fecha:** _______________  
**Lote / etiqueta:** _______________  
**Responsable:** _______________  
