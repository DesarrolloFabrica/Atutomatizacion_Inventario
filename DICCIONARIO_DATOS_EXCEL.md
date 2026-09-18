# Diccionario de datos — RUTAS.xlsx

Archivo de entrada del flujo. **Una fila = un lote** a procesar.

Ubicación habitual (ajustar si cambias de PC):

```text
C:\Users\angie_vera\Downloads\RUTAS.xlsx
```

La ruta exacta también está fijada en `CLONACION_CARPETA/clone_carpeta_drive.py`.
Antes de correr cualquier script: **guarda y cierra el Excel**.


--------------------------------------------------
FORMATOS ACEPTADOS
--------------------------------------------------

Formato de 3 columnas:

| etiqueta | origen | destino |

Formato de 4 columnas (recomendado):

| cliente | etiqueta | origen | destino |

Los encabezados se leen en minúsculas (no importa si escribes `Cliente` o `cliente`).


--------------------------------------------------
COLUMNAS
--------------------------------------------------

## cliente

| Campo | Detalle |
|---|---|
| **Qué es** | Clasificación del lote (quién / qué tipo de carga). |
| **Obligatoria** | Sí en el formato de 4 columnas. En clonación no decide la copia; sí importa en la carga a GCP. |
| **Valores válidos** | `PRODUCTO`, `TANIA`, `LMS_correcciones` (y alias como `CORRECCIONES`, `LMS_CORRECCIONES`). |
| **Cómo se usa** | En `LMS_Fabrica` se traduce a cliente + raíz en Cloud SQL. |
| **Mapeo actual a GCP** | Ver tabla abajo. |
| **Ejemplo** | `PRODUCTO` |

### Mapeo actual Excel → Cloud SQL

| Valor en Excel | cliente en GCP | raíz en GCP |
|---|---|---|
| `PRODUCTO` | PRODUCTO | LMS_Carga |
| `TANIA` | TANIA | LMS_Carga |
| `LMS_correcciones` (y alias) | PRODUCTO | LMS_Carga |

Nota: `LMS_correcciones` es una **clasificación del lote**, no una carpeta raíz.
La raíz canónica en Drive/GCP es siempre `LMS_Carga`.
Si en Drive la carpeta destino se llama `LMS_CORRECCIONES`, el escaneo especial
de escuelas sigue aplicándose, pero en la base se guarda raíz `LMS_Carga`.


## etiqueta

| Campo | Detalle |
|---|---|
| **Qué es** | Apodo humano del lote (para logs, inventarios y correos). |
| **Obligatoria** | Recomendada. Si viene vacía, el clon pone `Fila N`. |
| **Se guarda en GCP** | No. Solo sirve para identificar el lote en operación. |
| **Ejemplo** | `Contaduria Q2 lote 12` |


## origen

| Campo | Detalle |
|---|---|
| **Qué es** | Carpeta de Google Drive **de donde** se copia. |
| **Obligatoria** | Sí para clonación. |
| **Formato** | URL de carpeta Drive o ID de carpeta. |
| **Uso en clon** | Se clona origen → destino. |
| **Uso en carga GCP** | Solo referencia; **no** se escanea. |
| **Ejemplo** | `https://drive.google.com/drive/folders/ID_AQUI` |


## destino

| Campo | Detalle |
|---|---|
| **Qué es** | Carpeta de Google Drive **hacia donde** se copia. |
| **Obligatoria** | Sí (clonación y carga GCP). |
| **Formato** | URL de carpeta Drive o ID de carpeta. |
| **Uso en clon** | Destino de la copia. |
| **Uso en carga GCP** | Es la **única** carpeta que se escanea para armar el CSV. |
| **Ejemplo** | `https://drive.google.com/drive/folders/ID_DESTINO` |


--------------------------------------------------
REGLAS DE LLENADO
--------------------------------------------------

1. Una fila = un lote. No mezclar varios destinos en la misma celda.
2. `origen` y `destino` deben ser carpetas válidas (URL o ID).
3. Cierra el Excel antes de ejecutar (si está abierto, falla la lectura).
4. En carga GCP: si el nombre tiene `G`+dígitos se usa ese código; si no, el stem (p. ej. Moodle).
5. El **nombre del programa** en GCP sale del **nombre de la carpeta en Drive**, no de la columna `etiqueta`.


--------------------------------------------------
QUE NO ES ESTE EXCEL
--------------------------------------------------

- No es el inventario (eso lo genera la clonación).
- No es el CSV que va a Cloud SQL (eso lo genera `generar_base_rutas.py`).
- Origen, destino y cliente del Excel son la fuente de rutas a procesar.


--------------------------------------------------
COLUMNAS ALIAS QUE ENTIENDE LMS_Fabrica
--------------------------------------------------

Además de los nombres oficiales, el escaneo a CSV puede reconocer:

- En lugar de `cliente`: `tipo`, `clasificacion`, `clasificación`
- En lugar de `etiqueta`: `programa` (si aplica)

Para el día a día, usar siempre: `cliente | etiqueta | origen | destino`.
