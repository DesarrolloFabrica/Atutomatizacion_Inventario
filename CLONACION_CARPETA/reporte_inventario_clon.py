"""
CLONACION_CARPETA — reporte_inventario_clon.py
---------------------------------------------
¿Quién lo llama?
    clone_carpeta_drive.py, al terminar de clonar las rutas del Excel.

¿Qué hace?
    Inventaría origen vs destino en Google Drive y arma un Excel de
    comparación (conteos, faltantes, estado por tema/materia).

¿Qué NO hace?
    NO clona carpetas. NO carga nada a GCP / base de datos. Solo reporta.

Cómo cuenta el material
    Por tipo de carpeta bajo cada tema (ACTIVIDADES MOODLE, CONTENIDOS,
    SCORM, FICHAS, etc.). No exige prefijo «G» en los nombres: usa los
    nombres reales de las carpetas en Drive.

Hojas del Excel
    Cómo leer, Resumen, Temas y materiales, Faltantes,
    Archivos faltantes, Detalle por carpeta.

Colores
    Verde = OK · Rojo = falta / sin material · Amarillo = vacío opcional.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

# MIME de carpeta en Drive (para distinguir carpetas de archivos).
MIME_FOLDER = "application/vnd.google-apps.folder"

# -------------------------------------------------------------------------
# TIPOS_MATERIAL
# Lista de nombres de carpeta que, dentro de un tema/materia, representan
# material didáctico. Se comparan origen vs clon por estos tipos.
# No hace falta prefijo «G»: el match es por nombre (normalizado a mayúsculas).
# -------------------------------------------------------------------------
TIPOS_MATERIAL = (
    "ACTIVIDADES MOODLE",
    "CONTENIDOS",
    "SCORM",
    "FICHAS",
    "GLOSARIO",
    "REVISTA",
    "PDF",
    "PORTADA MATERIA",
    "GUION GRÁFICO",
    "GUION PODCAST",
    "PODCAST",
    "QA",
)

# -------------------------------------------------------------------------
# TIPOS_CRITICOS
# Subconjunto de TIPOS_MATERIAL. Si existen pero están vacíos (0 archivos),
# el tema se marca como «SIN MATERIAL» (rojo / pendiente) porque sin ellos
# la migración quedaría incompleta.
# Los no críticos (p. ej. PODCAST, QA, guiones) pueden ir vacíos a propósito
# y solo generan aviso amarillo («Vacío opcional»).
# -------------------------------------------------------------------------
TIPOS_CRITICOS = frozenset(
    {
        "ACTIVIDADES MOODLE",
        "CONTENIDOS",
        "SCORM",
        "FICHAS",
        "GLOSARIO",
        "REVISTA",
        "PDF",
        "PORTADA MATERIA",
    }
)

# Estilos reutilizados en todas las hojas del reporte.
FILL_TITULO = PatternFill("solid", fgColor="1F4E79")
FILL_OK = PatternFill("solid", fgColor="C6EFCE")
FILL_AVISO = PatternFill("solid", fgColor="FFEB9C")
FILL_FALTA = PatternFill("solid", fgColor="FFC7CE")
FILL_CABECERA = PatternFill("solid", fgColor="D6EAF8")
FONT_BLANCO = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
FONT_CABECERA = Font(bold=True, name="Calibri", size=11)
THIN = Border(
    left=Side(style="thin", color="BFBFBF"),
    right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"),
    bottom=Side(style="thin", color="BFBFBF"),
)
WRAP = Alignment(wrap_text=True, vertical="center")


def _norm(nombre: str) -> str:
    """Normaliza el nombre de carpeta para comparar (mayúsculas, sin puntos finales)."""
    return (nombre or "").strip().rstrip(".").upper()


def _es_tipo_material(nombre: str) -> str | None:
    """
    Si `nombre` corresponde a un tipo de material conocido, devuelve ese tipo
    canónico (p. ej. «ACTIVIDADES MOODLE»). Si no, None.

    Caso especial: cualquier nombre que contenga «MOODLE» se trata como
    ACTIVIDADES MOODLE (por variaciones de nombre en Drive).
    """
    n = _norm(nombre)
    for tipo in TIPOS_MATERIAL:
        if n == tipo:
            return tipo
    if "MOODLE" in n:
        return "ACTIVIDADES MOODLE"
    return None


@dataclass
class NodoCarpeta:
    """Una carpeta del árbol de Drive, con conteos directos y del subárbol."""

    ruta_relativa: str
    nombre: str
    profundidad: int
    n_subcarpetas: int
    n_archivos_directos: int
    n_archivos_arbol: int
    nombres_archivos: list[str] = field(default_factory=list)
    subcarpetas: dict[str, str] = field(default_factory=dict)


def inventariar_arbol(svc, listar_hijos, root_id: str) -> dict[str, NodoCarpeta]:
    """
    Recorre recursivamente una carpeta de Drive y arma el inventario.

    Parámetros
        svc, listar_hijos: cliente Drive y función que lista hijos de una carpeta.
        root_id: ID de la carpeta raíz a inventariar (origen o destino del clon).

    Retorna
        Dict {ruta relativa → NodoCarpeta}. La raíz del lote usa la clave vacía ''.

    Cada nodo guarda: subcarpetas, archivos directos, total de archivos en el
    subárbol y nombres de archivos (para detectar faltantes nombre a nombre).
    """
    nodos: dict[str, NodoCarpeta] = {}

    def rec(folder_id: str, ruta: str, nombre: str, profundidad: int) -> int:
        # Lista hijos una sola vez; separa carpetas vs archivos por MIME.
        hijos = listar_hijos(svc, folder_id)
        carpetas = [h for h in hijos if h.get("mimeType") == MIME_FOLDER]
        archivos = [h for h in hijos if h.get("mimeType") != MIME_FOLDER]
        sub_map = {c["name"]: c["id"] for c in carpetas}
        total_arbol = len(archivos)
        for c in carpetas:
            hijo_ruta = f"{ruta}/{c['name']}" if ruta else c["name"]
            total_arbol += rec(c["id"], hijo_ruta, c["name"], profundidad + 1)
        nodos[ruta] = NodoCarpeta(
            ruta_relativa=ruta,
            nombre=nombre,
            profundidad=profundidad,
            n_subcarpetas=len(carpetas),
            n_archivos_directos=len(archivos),
            n_archivos_arbol=total_arbol,
            nombres_archivos=[a["name"] for a in archivos],
            subcarpetas=sub_map,
        )
        return total_arbol

    rec(root_id, "", "(raíz)", 0)
    return nodos


def archivos_planos(nodos: dict[str, NodoCarpeta]) -> list[str]:
    """Rutas de todos los archivos del árbol (carpeta/archivo), ordenadas."""
    out: list[str] = []
    for ruta, n in nodos.items():
        for nom in n.nombres_archivos:
            out.append(f"{ruta}/{nom}" if ruta else nom)
    out.sort(key=str.lower)
    return out


def _conteo_material(nodos: dict[str, NodoCarpeta], ruta_tema: str) -> dict[str, int | None]:
    """
    Cuenta archivos directos por tipo de material bajo un tema/materia.

    Para cada entrada de TIPOS_MATERIAL:
        - int  → la subcarpeta existe; valor = n_archivos_directos.
        - None → esa subcarpeta no está bajo el tema (no aplica).

    Así el reporte distingue «no hay carpeta» de «carpeta vacía (0)».
    """
    tema = nodos.get(ruta_tema)
    out: dict[str, int | None] = {t: None for t in TIPOS_MATERIAL}
    if not tema:
        return out
    for nombre_hijo in tema.subcarpetas:
        tipo = _es_tipo_material(nombre_hijo)
        if not tipo:
            continue
        ruta_hijo = f"{ruta_tema}/{nombre_hijo}" if ruta_tema else nombre_hijo
        hijo = nodos.get(ruta_hijo)
        if hijo:
            out[tipo] = hijo.n_archivos_directos
    return out


def detectar_temas(nodos: dict[str, NodoCarpeta]) -> list[str]:
    """
    Detecta carpetas «tema/materia»: aquellas que tienen al menos una
    subcarpeta de material (Moodle, SCORM, CONTENIDOS, etc.).

    No usa prefijo «G»; solo mira la estructura de subcarpetas.
    Devuelve las rutas relativas ordenadas.
    """
    temas: list[str] = []
    for ruta, nodo in nodos.items():
        if not ruta:
            continue
        if any(_es_tipo_material(n) for n in nodo.subcarpetas):
            temas.append(ruta)
    temas.sort(key=lambda r: r.lower())
    return temas


def _partir_programa_tema(ruta_tema: str) -> tuple[str, str]:
    """Separa la ruta en (programa/curso padre, nombre del tema)."""
    partes = [p for p in ruta_tema.split("/") if p]
    if not partes:
        return "", ""
    tema = partes[-1].rstrip(".").strip()
    programa = partes[-2].rstrip(".").strip() if len(partes) >= 2 else ""
    return programa, tema


def _estado_celda(orig: int | None, clon: int | None, critico: bool) -> str:
    """
    Texto de estado al comparar un conteo origen vs clon.

    None = la carpeta de ese tipo no existe en ese lado.
    `critico` indica si un 0/0 se trata como «SIN MATERIAL» o solo «Vacío opcional».
    """
    if orig is None and clon is None:
        return "No aplica (no hay esa carpeta)"
    if orig is not None and clon is None:
        return "FALTA EN CLON (no se copió la carpeta)"
    if orig is None and clon is not None:
        return "Solo en clon"
    assert orig is not None and clon is not None
    if orig > 0 and clon < orig:
        return "FALTA EN CLON (menos archivos que el origen)"
    if orig == 0 and clon == 0 and critico:
        return "SIN MATERIAL — revisar antes de migrar"
    if orig == 0 and clon == 0:
        return "Vacío (opcional / no crítico)"
    if clon >= orig and orig > 0:
        return "OK"
    return "Revisar"


def _pintar_estado(celda, texto: str) -> None:
    """Asigna el texto y el color de fondo según el estado (OK / falta / aviso)."""
    celda.value = texto
    if texto.startswith("OK"):
        celda.fill = FILL_OK
    elif texto.startswith("FALTA") or texto.startswith("SIN MATERIAL"):
        celda.fill = FILL_FALTA
    elif texto.startswith("Vacío") or texto.startswith("Revisar") or texto.startswith("Solo"):
        celda.fill = FILL_AVISO
    celda.alignment = WRAP
    celda.border = THIN


def _ajustar_columnas(hoja: Worksheet, anchos: list[int]) -> None:
    """Fija anchos de columna (índice 1-based de Excel)."""
    for i, w in enumerate(anchos, start=1):
        hoja.column_dimensions[get_column_letter(i)].width = w


def _escribir_cabecera(hoja: Worksheet, fila: int, titulos: list[str]) -> None:
    """Escribe la fila de títulos, congela paneles debajo y aplica estilo de cabecera."""
    for col, titulo in enumerate(titulos, start=1):
        c = hoja.cell(fila, col, titulo)
        c.fill = FILL_CABECERA
        c.font = FONT_CABECERA
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        c.border = THIN
    hoja.freeze_panes = f"A{fila + 1}"
    hoja.row_dimensions[fila].height = 32


def _titulo_hoja(hoja: Worksheet, texto: str, n_cols: int) -> None:
    """Barra de título azul en la fila 1, fusionada a lo ancho de las columnas."""
    hoja.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n_cols)
    c = hoja.cell(1, 1, texto)
    c.font = FONT_BLANCO
    c.fill = FILL_TITULO
    c.alignment = Alignment(vertical="center", horizontal="left")
    hoja.row_dimensions[1].height = 22


def generar_reporte_excel(
    svc,
    listar_hijos,
    trabajos: list[dict],
    salida: Path,
) -> Path:
    """
    Genera el .xlsx de inventario post-clonación (origen vs destino).

    Lo invoca clone_carpeta_drive.py. No clona ni carga a GCP: solo inventaría
    y escribe el Excel.

    Parámetros
        svc, listar_hijos: acceso a Drive (mismo patrón que el clon).
        trabajos: lista que arma el clon; cada dict trae etiqueta, origen_id,
            destino_id, origen_nombre, destino_nombre.
        salida: ruta del archivo .xlsx a guardar.

    Retorna
        (ruta del Excel guardado, lista de resúmenes cortos para el correo).

    Flujo por cada trabajo
        1. Inventariar árbol origen y árbol destino.
        2. Detectar temas y comparar TIPOS_MATERIAL (críticos vs opcionales).
        3. Llenar hojas Resumen / Temas / Faltantes / Archivos / Detalle.
    """
    wb = Workbook()

    # --- Hoja «Cómo leer»: leyenda para quien abre el Excel ---
    leyenda = wb.active
    leyenda.title = "Cómo leer"
    _titulo_hoja(leyenda, "Reporte de clonación — inventario antes de migrar a base de datos", 2)
    lineas = [
        ("Para qué sirve", "Revisar qué se clonó y qué temas/materias aún no tienen material, antes de cargar a la base de datos."),
        ("Cuándo se genera", "Al terminar todas las rutas del Excel de clonación."),
        ("Hoja «Resumen»", "Totales por ruta: carpetas, archivos, actividades Moodle y temas con faltantes."),
        ("Hoja «Temas y materiales»", "Una fila por tema/materia. Columnas = tipo de material (Moodle, SCORM, contenidos, etc.)."),
        ("Hoja «Faltantes»", "Solo lo que hay que atender: carpeta no clonada, menos archivos, o material vacío."),
        ("Hoja «Archivos faltantes»", "Nombre por nombre: archivos que están en origen y no en el clon."),
        ("Hoja «Detalle por carpeta»", "Conteo de cada carpeta del árbol (origen vs clon)."),
        ("OK (verde)", "El clon tiene al menos los mismos archivos que el origen."),
        ("SIN MATERIAL (rojo)", "La carpeta existe pero no tiene archivos. El tema quedaría incompleto en la migración."),
        ("FALTA EN CLON (rojo)", "En el origen sí hay archivos (o la carpeta) y en el clon no."),
        ("Vacío opcional (amarillo)", "Carpetas como PODCAST o QA que a veces van vacías a propósito."),
        ("Actividad Moodle", "Cada archivo dentro de la carpeta «ACTIVIDADES MOODLE» cuenta como una actividad."),
        ("Tema / materia", "Carpeta que contiene subcarpetas de material (Moodle, SCORM, contenidos, fichas…)."),
    ]
    leyenda["A2"] = "Concepto"
    leyenda["B2"] = "Significado"
    leyenda["A2"].font = FONT_CABECERA
    leyenda["B2"].font = FONT_CABECERA
    leyenda["A2"].fill = FILL_CABECERA
    leyenda["B2"].fill = FILL_CABECERA
    for i, (k, v) in enumerate(lineas, start=3):
        c1 = leyenda.cell(i, 1, k)
        c2 = leyenda.cell(i, 2, v)
        c1.alignment = WRAP
        c2.alignment = WRAP
        c1.border = THIN
        c2.border = THIN
        if k.startswith("OK"):
            c1.fill = FILL_OK
            c2.fill = FILL_OK
        elif k.startswith("SIN MATERIAL") or k.startswith("FALTA EN CLON"):
            c1.fill = FILL_FALTA
            c2.fill = FILL_FALTA
        elif k.startswith("Vacío opcional"):
            c1.fill = FILL_AVISO
            c2.fill = FILL_AVISO
        leyenda.row_dimensions[i].height = 36
    _ajustar_columnas(leyenda, [28, 100])

    # --- Resto de hojas (cabeceras fijas; filas se llenan por trabajo) ---
    hoja_res = wb.create_sheet("Resumen")
    hoja_tem = wb.create_sheet("Temas y materiales")
    hoja_fal = wb.create_sheet("Faltantes")
    hoja_arc = wb.create_sheet("Archivos faltantes")
    hoja_det = wb.create_sheet("Detalle por carpeta")

    _titulo_hoja(hoja_res, "Resumen por ruta clonada", 10)
    hoja_res["A2"] = f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    _escribir_cabecera(
        hoja_res,
        3,
        [
            "Etiqueta (Excel)",
            "Carpeta origen",
            "Carpeta clon (destino)",
            "Carpetas (origen)",
            "Carpetas (clon)",
            "Archivos (origen)",
            "Archivos (clon)",
            "Actividades Moodle (origen)",
            "Actividades Moodle (clon)",
            "Temas con faltante de material",
        ],
    )
    _ajustar_columnas(hoja_res, [22, 36, 36, 16, 16, 16, 16, 22, 22, 28])

    cols_tema = [
        "Etiqueta",
        "Programa / curso padre",
        "Tema / materia",
        "Ruta en Drive",
        "Actividades Moodle (origen)",
        "Actividades Moodle (clon)",
        "Estado Moodle",
        "CONTENIDOS origen",
        "CONTENIDOS clon",
        "SCORM origen",
        "SCORM clon",
        "FICHAS origen",
        "FICHAS clon",
        "GLOSARIO origen",
        "GLOSARIO clon",
        "REVISTA origen",
        "REVISTA clon",
        "PDF origen",
        "PDF clon",
        "PORTADA origen",
        "PORTADA clon",
        "Archivos totales del tema (origen)",
        "Archivos totales del tema (clon)",
        "Diagnóstico",
    ]
    _titulo_hoja(hoja_tem, "Temas y materiales — identifique qué falta antes de migrar", len(cols_tema))
    hoja_tem["A2"] = "Filtre por «Diagnóstico» o por «Estado Moodle». Una fila = un tema/materia."
    _escribir_cabecera(hoja_tem, 3, cols_tema)
    _ajustar_columnas(
        hoja_tem,
        [16, 40, 40, 55, 14, 14, 28, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 10, 10, 12, 12, 16, 16, 42],
    )

    cols_fal = [
        "Prioridad",
        "Etiqueta",
        "Programa / curso padre",
        "Tema / materia",
        "Tipo de material",
        "Qué pasó",
        "Archivos en origen",
        "Archivos en clon",
        "Ruta",
    ]
    _titulo_hoja(hoja_fal, "Pendientes: materiales faltantes o clon incompleto", len(cols_fal))
    hoja_fal["A2"] = "Alta = no se puede migrar ese tema completo. Media = vacío opcional o diferencia menor."
    _escribir_cabecera(hoja_fal, 3, cols_fal)
    _ajustar_columnas(hoja_fal, [12, 16, 40, 40, 22, 50, 16, 16, 60])

    cols_arc = ["Etiqueta", "Ruta de la carpeta", "Nombre del archivo que falta"]
    _titulo_hoja(hoja_arc, "Archivos del origen que no están en el clon (nombre por nombre)", 3)
    hoja_arc["A2"] = "Úsela para saber exactamente qué copiar o qué falló."
    _escribir_cabecera(hoja_arc, 3, cols_arc)
    _ajustar_columnas(hoja_arc, [16, 80, 50])

    cols_det = [
        "Etiqueta",
        "Ruta relativa",
        "Nombre de carpeta",
        "Subcarpetas origen",
        "Subcarpetas clon",
        "Archivos directos origen",
        "Archivos directos clon",
        "Archivos en el árbol origen",
        "Archivos en el árbol clon",
        "¿Es carpeta de material?",
        "Estado",
    ]
    _titulo_hoja(hoja_det, "Detalle: cada carpeta del árbol", len(cols_det))
    _escribir_cabecera(hoja_det, 3, cols_det)
    _ajustar_columnas(hoja_det, [16, 70, 36, 16, 14, 18, 18, 18, 18, 22, 40])

    fila_res = 4
    fila_tem = 4
    fila_fal = 4
    fila_arc = 4
    fila_det = 4
    resumenes: list[dict] = []

    # --- Un bloque por ruta clonada (cada «trabajo» del Excel de clonación) ---
    for trabajo in trabajos:
        etiqueta = trabajo["etiqueta"]
        print(f"  Inventariando origen «{trabajo['origen_nombre']}»…", flush=True)
        nodos_o = inventariar_arbol(svc, listar_hijos, trabajo["origen_id"])
        print(f"  Inventariando clon «{trabajo['destino_nombre']}»…", flush=True)
        nodos_c = inventariar_arbol(svc, listar_hijos, trabajo["destino_id"])

        raiz_o = nodos_o[""]
        raiz_c = nodos_c[""]
        # Actividades Moodle = archivos directos dentro de carpetas de ese tipo.
        moodle_o = sum(
            n.n_archivos_directos
            for n in nodos_o.values()
            if _es_tipo_material(n.nombre) == "ACTIVIDADES MOODLE"
        )
        moodle_c = sum(
            n.n_archivos_directos
            for n in nodos_c.values()
            if _es_tipo_material(n.nombre) == "ACTIVIDADES MOODLE"
        )

        # Temas presentes en origen, en clon, o en ambos.
        temas = sorted(set(detectar_temas(nodos_o)) | set(detectar_temas(nodos_c)))
        temas_con_falta = 0

        for ruta_tema in temas:
            programa, tema = _partir_programa_tema(ruta_tema)
            mat_o = _conteo_material(nodos_o, ruta_tema)
            mat_c = _conteo_material(nodos_c, ruta_tema)
            no_o = nodos_o.get(ruta_tema)
            no_c = nodos_c.get(ruta_tema)
            tot_o = no_o.n_archivos_arbol if no_o else 0
            tot_c = no_c.n_archivos_arbol if no_c else 0

            est_moodle = _estado_celda(
                mat_o["ACTIVIDADES MOODLE"],
                mat_c["ACTIVIDADES MOODLE"],
                True,
            )
            problemas: list[str] = []
            if no_o and not no_c:
                problemas.append("El tema no está en el clon")
            for tipo in TIPOS_MATERIAL:
                est = _estado_celda(mat_o[tipo], mat_c[tipo], tipo in TIPOS_CRITICOS)
                if est.startswith("FALTA") or est.startswith("SIN MATERIAL"):
                    problemas.append(f"{tipo}: {est}")
                    prioridad = "Alta"
                    hoja_fal.cell(fila_fal, 1, prioridad)
                    hoja_fal.cell(fila_fal, 2, etiqueta)
                    hoja_fal.cell(fila_fal, 3, programa)
                    hoja_fal.cell(fila_fal, 4, tema)
                    hoja_fal.cell(fila_fal, 5, tipo)
                    hoja_fal.cell(fila_fal, 6, est)
                    vo = mat_o[tipo]
                    vc = mat_c[tipo]
                    hoja_fal.cell(fila_fal, 7, "" if vo is None else vo)
                    hoja_fal.cell(fila_fal, 8, "" if vc is None else vc)
                    hoja_fal.cell(fila_fal, 9, ruta_tema)
                    for col in range(1, 10):
                        hoja_fal.cell(fila_fal, col).border = THIN
                        hoja_fal.cell(fila_fal, col).alignment = WRAP
                    hoja_fal.cell(fila_fal, 1).fill = FILL_FALTA
                    fila_fal += 1
                elif est.startswith("Vacío"):
                    hoja_fal.cell(fila_fal, 1, "Media")
                    hoja_fal.cell(fila_fal, 2, etiqueta)
                    hoja_fal.cell(fila_fal, 3, programa)
                    hoja_fal.cell(fila_fal, 4, tema)
                    hoja_fal.cell(fila_fal, 5, tipo)
                    hoja_fal.cell(fila_fal, 6, est)
                    hoja_fal.cell(fila_fal, 7, 0)
                    hoja_fal.cell(fila_fal, 8, 0)
                    hoja_fal.cell(fila_fal, 9, ruta_tema)
                    for col in range(1, 10):
                        hoja_fal.cell(fila_fal, col).border = THIN
                        hoja_fal.cell(fila_fal, col).alignment = WRAP
                    hoja_fal.cell(fila_fal, 1).fill = FILL_AVISO
                    fila_fal += 1

            if problemas:
                temas_con_falta += 1
                diag = " | ".join(problemas[:6])
            else:
                diag = "Listo para revisar migración (material crítico presente)"

            vals = [
                etiqueta,
                programa,
                tema,
                ruta_tema,
                mat_o["ACTIVIDADES MOODLE"],
                mat_c["ACTIVIDADES MOODLE"],
                est_moodle,
                mat_o["CONTENIDOS"],
                mat_c["CONTENIDOS"],
                mat_o["SCORM"],
                mat_c["SCORM"],
                mat_o["FICHAS"],
                mat_c["FICHAS"],
                mat_o["GLOSARIO"],
                mat_c["GLOSARIO"],
                mat_o["REVISTA"],
                mat_c["REVISTA"],
                mat_o["PDF"],
                mat_c["PDF"],
                mat_o["PORTADA MATERIA"],
                mat_c["PORTADA MATERIA"],
                tot_o,
                tot_c,
                diag,
            ]
            for col, val in enumerate(vals, start=1):
                celda = hoja_tem.cell(fila_tem, col, "" if val is None else val)
                celda.border = THIN
                celda.alignment = WRAP
            _pintar_estado(hoja_tem.cell(fila_tem, 7), est_moodle)
            if problemas:
                hoja_tem.cell(fila_tem, 24).fill = FILL_FALTA
            else:
                hoja_tem.cell(fila_tem, 24).fill = FILL_OK
            fila_tem += 1

        valores_res = [
            etiqueta,
            trabajo["origen_nombre"],
            trabajo["destino_nombre"],
            max(len(nodos_o) - 1, 0),
            max(len(nodos_c) - 1, 0),
            raiz_o.n_archivos_arbol,
            raiz_c.n_archivos_arbol,
            moodle_o,
            moodle_c,
            temas_con_falta,
        ]
        for col, val in enumerate(valores_res, start=1):
            celda = hoja_res.cell(fila_res, col, val)
            celda.border = THIN
            celda.alignment = WRAP
        if temas_con_falta:
            hoja_res.cell(fila_res, 10).fill = FILL_FALTA
        else:
            hoja_res.cell(fila_res, 10).fill = FILL_OK
        fila_res += 1

        # Detalle carpeta a carpeta + archivos faltantes por nombre.
        rutas_todas = sorted(
            (set(nodos_o) | set(nodos_c)),
            key=lambda r: r.lower(),
        )
        faltan_en_clon = False
        extras_en_clon = False
        for ruta in rutas_todas:
            no = nodos_o.get(ruta)
            nc = nodos_c.get(ruta)
            nombre = (no or nc).nombre if (no or nc) else ""
            tipo = _es_tipo_material(nombre) or ""
            if no and not nc:
                est = "FALTA EN CLON"
                faltan_en_clon = True
            elif nc and not no:
                est = "Solo en clon"
                extras_en_clon = True
            elif no and nc:
                if no.n_archivos_directos == nc.n_archivos_directos:
                    est = "OK"
                elif nc.n_archivos_directos < no.n_archivos_directos:
                    est = "FALTA EN CLON (menos archivos)"
                    faltan_en_clon = True
                else:
                    est = "Clon tiene más archivos"
                    extras_en_clon = True
            else:
                est = "Revisar"
            det = [
                etiqueta,
                ruta or "(raíz de la carpeta)",
                nombre,
                no.n_subcarpetas if no else "",
                nc.n_subcarpetas if nc else "",
                no.n_archivos_directos if no else "",
                nc.n_archivos_directos if nc else "",
                no.n_archivos_arbol if no else "",
                nc.n_archivos_arbol if nc else "",
                tipo,
                est,
            ]
            for col, val in enumerate(det, start=1):
                celda = hoja_det.cell(fila_det, col, val)
                celda.border = THIN
                celda.alignment = WRAP
            _pintar_estado(hoja_det.cell(fila_det, 11), est)
            fila_det += 1
            nombres_o = list(no.nombres_archivos) if no else []
            nombres_c = list(nc.nombres_archivos) if nc else []
            for nom_f in sorted((Counter(nombres_o) - Counter(nombres_c)).elements()):
                hoja_arc.cell(fila_arc, 1, etiqueta).border = THIN
                hoja_arc.cell(fila_arc, 2, ruta or "(raíz)").border = THIN
                hoja_arc.cell(fila_arc, 2).alignment = WRAP
                hoja_arc.cell(fila_arc, 3, nom_f).border = THIN
                hoja_arc.cell(fila_arc, 3).fill = FILL_FALTA
                fila_arc += 1

        n_carp_o = max(len(nodos_o) - 1, 0)
        n_carp_c = max(len(nodos_c) - 1, 0)
        # OK solo si el clon no tiene de menos NI de más respecto al origen.
        validacion_ok = not faltan_en_clon and not extras_en_clon
        resumenes.append(
            {
                "etiqueta": etiqueta,
                "origen_nombre": trabajo["origen_nombre"],
                "destino_nombre": trabajo["destino_nombre"],
                "destino_id": trabajo["destino_id"],
                "enlace": f"https://drive.google.com/drive/folders/{trabajo['destino_id']}",
                "carpetas_origen": n_carp_o,
                "carpetas_clon": n_carp_c,
                "archivos_origen": raiz_o.n_archivos_arbol,
                "archivos_clon": raiz_c.n_archivos_arbol,
                "moodle_origen": moodle_o,
                "moodle_clon": moodle_c,
                "temas_con_falta": temas_con_falta,
                "validacion_ok": validacion_ok,
                "extras_en_clon": extras_en_clon,
                "archivos": archivos_planos(nodos_c),
            }
        )

    if fila_fal == 4:
        hoja_fal.cell(4, 1, "Sin pendientes críticos ni vacíos opcionales en esta corrida.")
        hoja_fal.merge_cells("A4:I4")

    if fila_arc == 4:
        hoja_arc.cell(4, 1, "No faltan archivos por nombre respecto al origen.")
        hoja_arc.merge_cells("A4:C4")

    hoja_res.auto_filter.ref = f"A3:J{max(fila_res - 1, 3)}"
    hoja_tem.auto_filter.ref = f"A3:X{max(fila_tem - 1, 3)}"
    hoja_fal.auto_filter.ref = f"A3:I{max(fila_fal - 1, 3)}"
    hoja_arc.auto_filter.ref = f"A3:C{max(fila_arc - 1, 3)}"
    hoja_det.auto_filter.ref = f"A3:K{max(fila_det - 1, 3)}"

    salida.parent.mkdir(parents=True, exist_ok=True)
    wb.save(salida)
    return salida, resumenes
