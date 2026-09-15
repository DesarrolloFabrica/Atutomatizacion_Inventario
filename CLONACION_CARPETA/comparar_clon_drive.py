"""
CLONACION_CARPETA — comparar_clon_drive.py
-----------------------------------------
Herramienta de DIAGNÓSTICO (uso manual).

Qué hace: compara dos IDs fijos de Drive (origen vs clon) y escribe un
reporte de texto con diferencias de carpetas/archivos.

Qué NO es:
  - No es el paso diario del flujo.
  - No lo llama clone_carpeta_drive.py.
  - El inventario “oficial” del flujo es reporte_inventario_clon + Google Sheets.

Cuándo usarlo: si sospechas que el clon quedó mal y quieres un cotejo extra
ruta por ruta, aparte del inventario automático.

Antes de correr: actualizar CARPETA_ORIGEN y CARPETA_DESTINO con los IDs reales.
Requiere token.json (no se sube a Git).
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------

# Tipos modernos (str | None, etc.).
from __future__ import annotations

# Errores HTTP de bajo nivel (para reintentar).
import http.client

# Leer token.json (sesión OAuth guardada).
import json

# (reservado / usado en otras partes del módulo si hay espera aleatoria).
import random

# Errores de red / SSL al hablar con la API.
import socket
import ssl
import sys
import time

# Estructuras simples para totales y líneas del reporte.
from dataclasses import dataclass, field

# Ruta del token y del archivo de salida.
from pathlib import Path

# Renovar token si expiró.
from google.auth.transport.requests import Request

# Credenciales de usuario Google.
from google.oauth2.credentials import Credentials

# Cliente API Drive.
from googleapiclient.discovery import build

# Errores HTTP de Google (429, 500, etc.).
from googleapiclient.errors import HttpError

# --- IDs fijos de la ÚLTIMA corrida de prueba (cambiarlos según el lote) ---
CARPETA_ORIGEN = "1Q3EHuRPUvAdIGQCFkZuHABLZvT9UtDBq"
CARPETA_DESTINO = "1H9RM9UzUt7ISi398dyjVxyEM7T1yfMiC"

# Permisos mínimos para leer Drive (aquí no se envía correo).
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
MIME_FOLDER = "application/vnd.google-apps.folder"
BASE = Path(__file__).resolve().parent
TOKEN_PATH = BASE / "token.json"
SALIDA = BASE / "reporte_comparacion_clon.txt"


def cargar_credenciales() -> Credentials:
    """
    # Aquí se lee token.json y se arma el objeto Credentials.
    Si el token venció, lo renueva y vuelve a guardar token.json.
    (No usa credentials.json: asume que ya autorizaste antes con el clon.)
    """
    # Abre el archivo de sesión OAuth.
    with TOKEN_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    # Convierte el JSON en credenciales usables por la API.
    creds = Credentials.from_authorized_user_info(data, SCOPES)
    if not creds:
        raise SystemExit("Credenciales inválidas")

    # Si expiró pero hay refresh_token, pide uno nuevo a Google y lo guarda.
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with TOKEN_PATH.open("w", encoding="utf-8") as t:
            t.write(creds.to_json())
    return creds


def ejecutar(req, max_intentos: int = 12):
    """
    # Aquí se ejecuta una petición a la API de Drive con reintentos.
    - Errores “duros” (400, 401, 403, 404): falla ya (no tiene sentido reintentar).
    - Errores temporales (429, 5xx, red caída): espera y vuelve a intentar.
    """
    ultimo: Exception | None = None
    for intento in range(max_intentos):
        try:
            # Ejecuta la petición (Google también reintenta por dentro hasta 5 veces).
            return req.execute(num_retries=5)
        except HttpError as e:
            st = e.resp.status
            # Errores de cliente / permiso / no encontrado → abortar.
            if st in (400, 401, 403, 404):
                raise
            # Solo reintentar timeouts, rate limit y errores de servidor.
            if st not in (408, 429) and not (500 <= st <= 599):
                raise
            ultimo = e
        except (
            http.client.IncompleteRead,
            http.client.RemoteDisconnected,
            socket.gaierror,
            socket.error,
            ConnectionError,
            OSError,
            ssl.SSLError,
        ) as e:
            # Problemas de red/SSL: guardar y reintentar.
            ultimo = e
        # Espera creciente entre intentos (backoff), máximo 90 segundos.
        if intento < max_intentos - 1:
            time.sleep(min(2**intento * 0.5, 90.0))
    if ultimo is not None:
        raise ultimo
    raise RuntimeError("Error en la petición")


def listar_hijos(svc, parent_id: str) -> list[dict]:
    """
    Lista TODOS los hijos directos de una carpeta Drive (no recursivo).

    - Pide páginas de 200 hasta agotar nextPageToken.
    - Solo id, name y mimeType (basta para comparar nombres).
    - Incluye Shared Drives (supportsAllDrives).
    - Ignora papelera (trashed = false).
    """
    out: list[dict] = []
    page = None
    while True:
        # Query: hijos de este padre y no en papelera.
        q = f"'{parent_id}' in parents and trashed = false"
        r = ejecutar(
            svc.files()
            .list(
                q=q,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page,
                pageSize=200,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
        )
        out.extend(r.get("files", []))
        page = r.get("nextPageToken")
        if not page:
            break
    return out


def partidir(hijos: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Separa la lista de hijos en (carpetas, archivos) y ordena por nombre.

    Así comparar() puede cotejar nombres de subcarpetas y de archivos
    por separado, sin mezclar tipos.
    """
    c, a = [], []
    for h in hijos:
        # mimeType de carpeta → lista de carpetas; el resto → archivos.
        (c if h["mimeType"] == MIME_FOLDER else a).append(h)
    c.sort(key=lambda x: (x["name"] or "").lower())
    a.sort(key=lambda x: (x["name"] or "").lower())
    return c, a


@dataclass
class TotalesAcumulados:
    carpetas: int = 0
    archivos: int = 0

    def add_tree(self, subfolders: int, files: int) -> None:
        self.carpetas += subfolders
        self.archivos += files


@dataclass
class LineaDiferencia:
    ruta: str
    f_o: int
    a_o: int
    f_c: int
    a_c: int
    ok: bool
    faltan_c: list[str] = field(default_factory=list)
    sobran_c: list[str] = field(default_factory=list)
    faltan_a: list[str] = field(default_factory=list)
    sobran_a: list[str] = field(default_factory=list)
    hija_destino: str | None = None


def buscar_carpeta_por_nombre(
    subcarpetas: list[dict], nombre: str
) -> str | None:
    for c in subcarpetas:
        if c["name"] == nombre:
            return c["id"]
    return None


def comparar(
    svc,
    id_orig: str,
    id_clon: str,
    ruta: str,
    lineas: list[LineaDiferencia],
    totales_orig: TotalesAcumulados,
    totales_clon: TotalesAcumulados,
) -> bool:
    """
    Compara recursivamente un par de carpetas (origen vs clon) por NOMBRE.

    Flujo tutorial:
      1) Lista hijos de ambas carpetas y los parte en subcarpetas / archivos.
      2) Calcula faltan/sobran (solo en origen o solo en clon).
      3) Guarda una LineaDiferencia para esta ruta (conteos directos + diffs).
      4) Acumula totales de hijos directos (para el resumen del reporte).
      5) Por cada subcarpeta del origen: si no está en el clon, marca
         “carpeta completa” faltante; si está, llama a comparar() otra vez.

    Devuelve False si en esta rama (o abajo) hay huecos o diferencias.
    """
    # Paso 1: hijos directos de cada lado.
    h_o = listar_hijos(svc, id_orig)
    h_c = listar_hijos(svc, id_clon) if id_clon else []
    c_o, a_o = partidir(h_o)
    c_c, a_c = partidir(h_c)

    # Paso 2: diferencias de nombres (carpetas = sets; archivos = sets de nombres).
    nom_carp_o = {x["name"] for x in c_o}
    nom_carp_c = {x["name"] for x in c_c}
    nom_a_o = [x["name"] for x in a_o]
    nom_a_c = [x["name"] for x in a_c]
    faltan_c = sorted(nom_carp_o - nom_carp_c)
    sobran_c = sorted(nom_carp_c - nom_carp_o)
    faltan_a = sorted(set(nom_a_o) - set(nom_a_c))
    sobran_a = sorted(set(nom_a_c) - set(nom_a_o))

    coincide = not (faltan_c or faltan_a or sobran_c or sobran_a)

    # Paso 3–4: una línea del reporte + sumas de hijos directos.
    lineas.append(
        LineaDiferencia(
            ruta=ruta,
            f_o=len(c_o),
            a_o=len(a_o),
            f_c=len(c_c),
            a_c=len(a_c),
            ok=coincide,
            faltan_c=faltan_c,
            sobran_c=sobran_c,
            faltan_a=faltan_a,
            sobran_a=sobran_a,
        )
    )
    totales_orig.add_tree(len(c_o), len(a_o))
    totales_clon.add_tree(len(c_c), len(a_c))

    # Paso 5: bajar recursivamente por cada subcarpeta del origen.
    al_ok = True
    for c in c_o:
        n = c["name"]
        cid = buscar_carpeta_por_nombre(c_c, n)
        subruta = f"{ruta}/{n}" if ruta else n
        if cid is None:
            # La carpeta entera falta en el clon: no se puede cotejar debajo.
            lineas.append(
                LineaDiferencia(
                    ruta=subruta,
                    f_o=0,
                    a_o=0,
                    f_c=0,
                    a_c=0,
                    ok=False,
                    faltan_c=[n + " (carpeta completa)"],
                )
            )
            al_ok = False
            continue
        if not comparar(
            svc, c["id"], cid, subruta, lineas, totales_orig, totales_clon
        ):
            al_ok = False
    return al_ok


def contar_todo(svc, root_id: str) -> tuple[int, int]:
    """
    Recorre TODO el árbol bajo root_id (BFS con pila) y cuenta:
      - subcarpetas (cada nodo carpeta una vez; la raíz NO cuenta),
      - archivos hoja (cada archivo una vez).

    Sirve para el bloque “Total REAL” del reporte, distinto de los
    totales por ruta (que suman hijos directos en cada nivel).
    """
    carpetas = 0
    archivos = 0
    # Pila de IDs de carpeta por visitar (empieza en la raíz).
    stack: list[str] = [root_id]
    while stack:
        pid = stack.pop()
        cts, a = partidir(listar_hijos(svc, pid))
        for f in cts:
            carpetas += 1
            stack.append(f["id"])  # seguir bajando
        archivos += len(a)
    return carpetas, archivos


def main() -> None:
    """
    Punto de entrada manual:
      1) Exige token.json
      2) Lee origen/destino (IDs fijos arriba)
      3) Compara árboles
      4) Imprime y guarda reporte_comparacion_clon.txt
    """
    if not TOKEN_PATH.is_file():
        print("Falta token.json", file=sys.stderr)
        sys.exit(1)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    creds = cargar_credenciales()
    svc = build("drive", "v3", credentials=creds, static_discovery=True)

    m_o = ejecutar(
        svc.files().get(
            fileId=CARPETA_ORIGEN,
            fields="id, name, mimeType",
            supportsAllDrives=True,
        )
    )
    if m_o.get("mimeType") != MIME_FOLDER:
        print("Origen no es carpeta", file=sys.stderr)
        sys.exit(1)
    raiz_nombre = m_o["name"]

    m_c = ejecutar(
        svc.files().get(
            fileId=CARPETA_DESTINO,
            fields="id, name, mimeType",
            supportsAllDrives=True,
        )
    )
    if m_c.get("mimeType") != MIME_FOLDER:
        print("Destino no es carpeta", file=sys.stderr)
        sys.exit(1)
    id_clon = CARPETA_DESTINO

    lineas2: list[LineaDiferencia] = []
    to2_o = TotalesAcumulados()
    to2_c = TotalesAcumulados()

    ok_arbol = comparar(
        svc, CARPETA_ORIGEN, id_clon, raiz_nombre, lineas2, to2_o, to2_c
    )

    car_tot_o, ar_tot_o = contar_todo(svc, CARPETA_ORIGEN)
    car_tot_c, ar_tot_c = contar_todo(svc, id_clon)

    out: list[str] = []
    out.append("=== Comparación clon (google Drive) ===\n")
    out.append(f"Origen (ID): {CARPETA_ORIGEN}")
    out.append(f"Clon destino (ID): {CARPETA_DESTINO}  ->  \"{m_c['name']}\"\n")
    out.append("Por ruta: subcarpetas y archivos DIRECTOS en esa carpeta.\n")
    out.append("  [O] = origen, [C] = clon. [OK] = mismos nombres de items.\n")
    out.append("-" * 80)

    for L in lineas2:
        s = f"\nRuta: {L.ruta}\n"
        s += f"  [O]  subcarpetas: {L.f_o:4d}  |  archivos: {L.a_o:4d}\n"
        s += f"  [C]  subcarpetas: {L.f_c:4d}  |  archivos: {L.a_c:4d}\n"
        if L.ok:
            s += "  Estado: OK (mismos nombres; conteo directo coincide)\n"
        else:
            s += "  Estado: DIFERENCIAS\n"
            if L.faltan_c:
                s += f"  - Solo en ORIGEN (faltan en clon): {len(L.faltan_c)} subcarpeta(s) : {L.faltan_c[:20]}{'...' if len(L.faltan_c) > 20 else ''}\n"
            if L.faltan_a:
                s += f"  - Solo en ORIGEN (faltan en clon): {len(L.faltan_a)} archivo(s) : {L.faltan_a[:20]}{'...' if len(L.faltan_a) > 20 else ''}\n"
            if L.sobran_c:
                s += f"  - Solo en CLON (extra): {len(L.sobran_c)} subcarpeta(s) : {L.sobran_c[:10]}{'...' if len(L.sobran_c) > 10 else ''}\n"
            if L.sobran_a:
                s += f"  - Solo en CLON (extra): {len(L.sobran_a)} archivo(s) : {L.sobran_a[:10]}{'...' if len(L.sobran_a) > 10 else ''}\n"
        if L.faltan_c and L.faltan_c[0].endswith("(carpeta completa)"):
            s += "  (rama faltante en clon: no se pudo cotejar bajo ella)\n"
        out.append(s)

    out.append("\n" + "=" * 80)
    out.append("TOTALES (sumando hijos directos de cada carpeta recorrida; un archivo se cuenta en su carpeta padre una vez)\n")
    out.append(f"  Suma de subcarpetas (directas, todas las rutas):  origen = {to2_o.carpetas}  |  clon = {to2_c.carpetas}\n")
    out.append(f"  Suma de archivos (directos, todas las rutas):     origen = {to2_o.archivos}  |  clon = {to2_c.archivos}\n")
    out.append("\nTotal REAL en el árbol (cada nodo se cuenta una sola vez)\n")
    out.append("  - Carpetas (todas las subcarpetas, sin la raíz):  " f"origen = {car_tot_o}  |  clon = {car_tot_c}\n")
    out.append("  - Archivos (hojas del árbol):                     " f"origen = {ar_tot_o}  |  clon = {ar_tot_c}\n")
    if car_tot_o == car_tot_c and ar_tot_o == ar_tot_c and ok_arbol:
        out.append("\nCONCLUSION: Estructura y conteos alineados con el clon (cotejo ruta a ruta).\n")
    else:
        out.append("\nCONCLUSION: Hay diferencias; revisa las lineas con DIFERENCIAS arriba.\n")

    text = "\n".join(out)
    print(text)
    SALIDA.write_text(text, encoding="utf-8")
    print(f"\n(Reporte guardado en: {SALIDA})", file=sys.stderr)


if __name__ == "__main__":
    main()
