"""
Librería compartida del flujo LMS Fábrica.

Este módulo NO es solo un script de generación: concentra utilidades comunes
que reutilizan otros scripts del mismo directorio, entre ellos:
  - generar_base_rutas.py   (escaneo Drive + CSV de rutas)
  - cargar_base_gcp.py      (carga a Cloud SQL / GCP)
  - notificar_carga_lms.py  (notificaciones posteriores a la carga)

Qué ofrece aquí:
  - Autenticación OAuth con Google Drive (credenciales.json / token.json).
  - Parsers de rutas Drive y extracción de códigos de archivo (G + dígitos).
  - Definición de columnas CSV de salida (formato studio_results / desnormalizado).
  - IdResolver: resolución (y opcionalmente alta) de IDs contra Cloud SQL.
  - ReferenciaGcp: reutilización de IDs desde un CSV exportado de GCP.
  - generar(): orquestación Drive → filas CSV con IDs.

Esquema Cloud SQL por defecto: fabrica_pruebas (variable de entorno LMS_SCHEMA).

IMPORTANTE — no versionar secretos:
  credenciales.json, token.json y .env NO deben subirse a Git.
  Contienen OAuth y contraseñas de base de datos.
"""

from __future__ import annotations  # Aquí se habilitan anotaciones de tipos diferidas (Python 3.7+)

# --- Imports de la librería estándar ---
import argparse  # Aquí se parsean argumentos de línea de comandos
import csv  # Aquí se lee/escribe el CSV desnormalizado de salida
import json  # Aquí se usa (indirectamente) al serializar token OAuth a JSON
import os  # Aquí se leen variables de entorno (DB_*, LMS_SCHEMA)
import re  # Aquí se definen patrones de código G+dígitos y rutas
import sys  # Aquí se escriben avisos/errores a stderr
import unicodedata  # Aquí se normalizan acentos al comparar nombres de carpetas
from collections import deque  # Aquí se hace BFS al escanear carpetas de Drive
from datetime import datetime, timezone  # Aquí se marca archivo_fecha_registro en UTC
from pathlib import Path  # Aquí se resuelven rutas de archivos locales
from urllib.parse import parse_qs, urlparse  # Aquí se extrae el ID de carpeta desde una URL de Drive

# --- Imports de terceros (auth Google + Drive API) ---
from dotenv import load_dotenv  # Aquí se cargan DB_* y LMS_SCHEMA desde .env
from google.auth.exceptions import RefreshError  # Aquí se detecta token OAuth vencido/inválido
from google.auth.transport.requests import Request  # Aquí se refresca el token OAuth
from google.oauth2.credentials import Credentials  # Aquí se modelan las credenciales OAuth
from google_auth_oauthlib.flow import InstalledAppFlow  # Aquí se abre el flujo de login en navegador
from googleapiclient.discovery import build  # Aquí se construye el cliente de Drive API
from googleapiclient.errors import HttpError  # Aquí se capturan errores de la API de Drive

# --- Dependencia opcional: PostgreSQL / Cloud SQL ---
try:
    import psycopg2  # Aquí se conecta IdResolver a Cloud SQL
except ImportError:
    psycopg2 = None  # type: ignore  # Sin psycopg2, IdResolver trabaja solo con IDs locales

# --- Rutas locales del módulo (NO van a Git: credenciales, token, .env) ---
BASE_DIR = Path(__file__).resolve().parent  # Aquí se toma la carpeta LMS_Fabrica
TOKEN_PATH = BASE_DIR / "token.json"  # Aquí se guarda el token OAuth (NO subir a Git)
CREDENTIALS_PATH = BASE_DIR / "credenciales.json"  # Aquí está el client secret OAuth (NO subir a Git)
_ENV_CANDIDATES = [
    BASE_DIR / ".env",  # Preferido: .env junto a este script
    BASE_DIR.parent / "CARGA_LMS_GCP_INV" / ".env",  # Alternativa: .env del otro flujo
]
ENV_PATH = next((p for p in _ENV_CANDIDATES if p.exists()), _ENV_CANDIDATES[0])
load_dotenv(ENV_PATH)  # Aquí se cargan variables de DB / esquema (el .env NO va a Git)

# --- Constantes de negocio / Drive ---
CARPETA_DEFAULT = "1anQgYLj527YuLaxyZDpEEyYnUEJY97h0"  # ID de carpeta Drive por defecto
CLIENTES_VALIDOS = {"PRODUCTO", "TANIA"}  # Carpetas cliente permitidas bajo Q2
PAQUETES_VALIDOS = {"MODELO_NOTEBOOK", "NOTEBOOK", "MODELO_NOTEBOOK "}  # Nombres de paquete aceptados
RAIZ_DISPLAY = {"LMS_CARGA": "LMS_Carga"}  # Nombre “bonito” de raíz en el CSV
# Esquema Cloud SQL por defecto: fabrica_pruebas (override con LMS_SCHEMA en .env)
SCHEMA = os.getenv("LMS_SCHEMA", "fabrica_pruebas")

# Scopes OAuth: Drive (lectura/escritura), Sheets y Gmail (compartidos con otros scripts)
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
]
MIME_FOLDER = "application/vnd.google-apps.folder"  # MIME de carpeta en Drive
DRIVE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")  # Validación de IDs de Drive
# Patrones de indexación a GCP: el código de archivo/gránulo es G seguido de dígitos
# (ej. G12345, G12345_titulo.mp4). Solo esos archivos entran a la base.
PATRON_ARCHIVO = re.compile(r"^G(\d+)(?:[_\s].*)?$", re.IGNORECASE)
PATRON_CODIGO = re.compile(r"^G(\d+)", re.IGNORECASE)  # Regla de indexación: G + dígitos
PATRON_GRANULO_NOMBRE = re.compile(r"^(G\d+)_(.+)$", re.IGNORECASE)

# Columnas del CSV desnormalizado (mismo orden que studio_results / carga GCP)
COLUMNAS_SALIDA = [
    "archivo_id",
    "archivo_nombre",
    "archivo_nombre_original",
    "archivo_enlace",
    "archivo_hash",
    "archivo_fecha_registro",
    "archivo_activo",
    "granulo_id",
    "granulo_codigo",
    "granulo_nombre",
    "materia_id",
    "materia_semestre",
    "materia_nombre",
    "programa_id",
    "programa_nombre",
    "escuela_id",
    "escuela_nombre",
    "paquete_id",
    "paquete_nombre",
    "raiz_id",
    "raiz_nombre",
    "destinatario_id",
    "destinatario_codigo",
    "periodo_id",
    "periodo_codigo",
    "cliente_id",
    "cliente_nombre",
    "extension_id",
    "extension_tipo",
]

# Mapa fijo extensión → id conocido en GCP (evita crear filas duplicadas de extensión)
EXTENSION_MAP = {
    "mp3": 1,
    "mp4": 2,
    "pdf": 3,
    "png": 5,
    "gif": 665,
    "zip": 671,
}


def norm_text(value: object) -> str:
    """Normaliza texto: quita acentos, mayúsculas y deja solo A-Z0-9 unidos por _."""
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


# Paquetes válidos ya normalizados (comparación estable contra carpetas Drive)
PAQUETES_VALIDOS_NORM = {norm_text(p) for p in PAQUETES_VALIDOS}


def extraer_id_carpeta(entrada: str) -> str:
    """Extrae el ID de carpeta Drive desde una URL o desde un ID crudo."""
    texto = entrada.strip().strip('"')
    parsed = urlparse(texto)
    if parsed.scheme and parsed.netloc:
        partes = [p for p in parsed.path.split("/") if p]
        if "folders" in partes:
            idx = partes.index("folders") + 1
            if idx < len(partes) and DRIVE_ID_PATTERN.fullmatch(partes[idx]):
                return partes[idx]
        query_id = parse_qs(parsed.query).get("id", [""])[0]
        if query_id and DRIVE_ID_PATTERN.fullmatch(query_id):
            return query_id
        raise ValueError(f"No se pudo extraer ID de carpeta: {entrada}")
    if DRIVE_ID_PATTERN.fullmatch(texto):
        return texto
    raise ValueError(f"Valor no válido: {entrada}")


def autenticar_drive() -> Credentials:
    """Autentica OAuth con Drive: reutiliza token.json o abre login con credenciales.json."""
    creds: Credentials | None = None
    if TOKEN_PATH.exists():
        # Aquí se intenta reusar el token guardado localmente
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if creds and creds.scopes and not set(SCOPES) <= set(creds.scopes):
            creds = None  # Scopes insuficientes → forzar nuevo login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                # Aquí se refresca el access token sin abrir el navegador
                creds.refresh(Request())
            except RefreshError:
                creds = None
        if not creds or not creds.valid:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(f"Falta {CREDENTIALS_PATH}")
            # Aquí se abre el flujo OAuth en el navegador (Installed App)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        # Aquí se persiste el token para la próxima ejecución (archivo local, no Git)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def listar_hijos(servicio, parent_id: str) -> list[dict]:
    """Lista hijos directos de una carpeta Drive (paginado, incluye Shared Drives)."""
    hijos: list[dict] = []
    page_token: str | None = None
    while True:
        # Aquí se pide una página de archivos/carpetas bajo parent_id
        resp = (
            servicio.files()
            .list(
                q=f"'{parent_id}' in parents and trashed = false",
                pageSize=200,
                pageToken=page_token,
                orderBy="folder,name_natural",
                fields="nextPageToken,files(id,name,mimeType,webViewLink,fileExtension)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                corpora="allDrives",
            )
            .execute()
        )
        hijos.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            return hijos


def obtener_extension(archivo: dict) -> str:
    """Obtiene la extensión del archivo desde metadatos Drive o desde el nombre."""
    ext = archivo.get("fileExtension")
    if ext:
        return str(ext).lower()
    nombre = archivo.get("name", "")
    if "." in nombre:
        return Path(nombre).suffix.lstrip(".").lower()
    return ""


def extraer_codigo(nombre: str) -> str | None:
    """
    Extrae el código de indexación GCP: G + dígitos (PATRON_CODIGO).
    Ej.: 'G12345_titulo.mp4' → 'G12345'. Si no hay match, el archivo no se indexa.
    """
    candidatos = [Path(nombre).stem, nombre]
    for candidato in candidatos:
        m = PATRON_CODIGO.match(candidato)
        if m:
            return f"G{m.group(1)}"
    return None


def es_carpeta_granulo(nombre: str) -> bool:
    """True si el nombre (normalizado) empieza como código G+dígitos."""
    return bool(PATRON_CODIGO.match(norm_text(nombre)))


def extraer_id_archivo(enlace: str) -> str:
    """Extrae el file ID de un enlace tipo /file/d/<id>/..."""
    match = re.search(r"/file/d/([^/]+)", enlace or "")
    return match.group(1) if match else ""


def raiz_nombre_display(raiz: str) -> str:
    """Devuelve el nombre de raíz para mostrar en CSV (p. ej. LMS_Carga)."""
    return RAIZ_DISPLAY.get(norm_text(raiz), raiz)


def extraer_granulo_nombre(
    nombre_archivo: str, codigo: str, materia: str, granulo_carpeta: str = ""
) -> str:
    """Arma el nombre de gránulo: carpeta G*, patrón G#_texto, o codigo_materia."""
    if granulo_carpeta and PATRON_CODIGO.match(granulo_carpeta):
        return granulo_carpeta
    base = Path(nombre_archivo).stem
    m = PATRON_GRANULO_NOMBRE.match(base)
    if m:
        return norm_text(f"{m.group(1)}_{m.group(2)}")
    return norm_text(f"{codigo}_{materia}")


def parse_semestre(valor: str) -> int:
    """Convierte carpeta de semestre a entero 1–12 (propedéutico → 1)."""
    v = norm_text(valor)
    if v in {"PROPEDEUTICO", "PROP", "PRE", "PREPROPEDEUTICO"}:
        return 1
    try:
        n = int(float(v))
        return n if 1 <= n <= 12 else 1
    except ValueError:
        return 1


def parsear_ruta(partes: list[str]) -> dict[str, str] | None:
    """
    Interpreta la ruta de carpetas Drive y devuelve metadatos, o None si no aplica.

    Rutas soportadas:
    - .../paquete/materia/archivo                 (10 partes)
    - .../paquete/materia/granulo/archivo         (11 partes, NOTEBOOK/TANIA o MODELO_NOTEBOOK)
    - .../materia/granulo/archivo                 (10 partes, paquete = nombre de materia)
    """
    if len(partes) < 10:
        return None

    cliente = norm_text(partes[3])
    if cliente not in CLIENTES_VALIDOS:
        return None

    # Aquí se arma la base común de la jerarquía (raíz → semestre)
    base = {
        "raiz": partes[0],
        "destinatario": norm_text(partes[1]),
        "periodo": norm_text(partes[2]),
        "cliente": cliente,
        "escuela": norm_text(partes[4]),
        "programa": norm_text(partes[5]),
        "semestre": str(parse_semestre(partes[6])),
    }
    paquete = norm_text(partes[7])

    # Caso estándar: carpeta de paquete válido (NOTEBOOK / MODELO_NOTEBOOK)
    if paquete in PAQUETES_VALIDOS_NORM:
        materia = norm_text(partes[8])
        granulo_carpeta = norm_text(partes[9]) if len(partes) >= 11 else ""
        return {
            **base,
            "paquete": paquete,
            "materia": materia,
            "granulo_carpeta": granulo_carpeta,
            "granulo_modo_alt": False,
        }

    # Caso alterno: la carpeta tras el paquete ya es un gránulo G#
    if es_carpeta_granulo(partes[8]):
        return {
            **base,
            "paquete": paquete,
            "materia": norm_text(partes[8]),
            "granulo_carpeta": "",
            "granulo_modo_alt": True,
        }

    return None


def escanear_drive(servicio, folder_id: str) -> list[dict]:
    """
    Escanea Drive bajo la raíz dada y devuelve registros de archivos G*.

    Prioriza la rama estándar LMS_Carga > MEN > Q2 > PRODUCTO|TANIA > ...
    Solo incluye archivos cuyo nombre cumple la regla G+dígitos (indexación GCP).
    """
    # Aquí se obtiene el nombre de la carpeta raíz
    raiz = (
        servicio.files()
        .get(fileId=folder_id, fields="id,name", supportsAllDrives=True)
        .execute()
    )
    resultados: list[dict] = []

    def procesar_rama(pid: str, ruta: list[str]) -> None:
        """BFS: recorre carpetas; indexa archivos con código G+dígitos y ruta válida."""
        cola: deque[tuple[str, list[str]]] = deque([(pid, ruta)])
        while cola:
            actual_id, actual_ruta = cola.popleft()
            try:
                hijos = listar_hijos(servicio, actual_id)
            except HttpError as err:
                print(f"Aviso: no se pudo leer carpeta ({err})", file=sys.stderr, flush=True)
                continue

            for hijo in hijos:
                nombre = hijo.get("name", "")
                if hijo.get("mimeType") == MIME_FOLDER:
                    # Aquí se encola la subcarpeta para seguir bajando
                    cola.append((hijo["id"], [*actual_ruta, nombre]))
                    continue

                # Aquí se aplica la regla de indexación: solo archivos G+dígitos
                codigo = extraer_codigo(nombre)
                if not codigo:
                    continue

                meta = parsear_ruta([*actual_ruta, nombre])
                if not meta:
                    continue

                ext = obtener_extension(hijo)
                if meta.get("granulo_modo_alt"):
                    granulo_nombre = ""
                elif meta.get("granulo_carpeta"):
                    granulo_nombre = meta["granulo_carpeta"]
                else:
                    granulo_nombre = extraer_granulo_nombre(
                        nombre, codigo, meta["materia"], meta.get("granulo_carpeta", "")
                    )
                resultados.append(
                    {
                        **meta,
                        "codigo": codigo,
                        "granulo_nombre": granulo_nombre,
                        "archivo_nombre": nombre,
                        "archivo_nombre_original": nombre,
                        "archivo_enlace": hijo.get("webViewLink", ""),
                        "extension": ext,
                    }
                )

    nombre_raiz = raiz.get("name", "LMS_Carga")
    print(f"Raíz: {nombre_raiz}", flush=True)

    # Solo ramas estándar: LMS_Carga > MEN > Q2 > PRODUCTO|TANIA > ...
    hijos_raiz = listar_hijos(servicio, folder_id)
    men = next((h for h in hijos_raiz if norm_text(h.get("name", "")) == "MEN"), None)
    if not men:
        # Sin MEN: se escanea toda la raíz como fallback
        procesar_rama(folder_id, [nombre_raiz])
        return resultados

    hijos_men = listar_hijos(servicio, men["id"])
    q2 = next((h for h in hijos_men if norm_text(h.get("name", "")) == "Q2"), None)
    if not q2:
        procesar_rama(men["id"], [nombre_raiz, men["name"]])
        return resultados

    hijos_q2 = listar_hijos(servicio, q2["id"])
    clientes = [
        h for h in hijos_q2 if norm_text(h.get("name", "")) in CLIENTES_VALIDOS
    ]
    print(f"Clientes a procesar: {[c['name'] for c in clientes]}", flush=True)

    for cliente in clientes:
        print(f"  Escaneando {cliente['name']}...", flush=True)
        procesar_rama(
            cliente["id"],
            [nombre_raiz, men["name"], q2["name"], cliente["name"]],
        )
        print(f"  -> acumulado: {len(resultados)} archivos", flush=True)

    return resultados


class IdResolver:
    """
    Resuelve (y opcionalmente inserta) IDs de dimensiones en Cloud SQL.

    Usa el esquema SCHEMA (default: fabrica_pruebas). En modo readonly solo lee;
    con escritura crea filas nuevas. Sin conexión, asigna IDs locales consecutivos.
    """

    def __init__(self, readonly: bool = True):
        """Conecta a Cloud SQL si hay psycopg2 y .env; carga MAX(id) por tabla."""
        self.cache: dict = {}
        self.next_ids: dict[str, int] = {}
        self.conn = None
        self.readonly = readonly

        if psycopg2 is None or not ENV_PATH.exists():
            return

        load_dotenv(ENV_PATH)
        try:
            # Aquí se abre la conexión con variables del .env (NO versionar en Git)
            self.conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", "5432")),
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
            )
            self._cargar_max_ids()
            modo = "lectura" if readonly else "lectura/escritura"
            print(f"Conectado a Cloud SQL ({modo}) esquema={SCHEMA}.")
        except Exception as exc:
            print(f"Aviso: sin conexión a GCP ({exc}). IDs locales.", file=sys.stderr)
            self.conn = None

    def _cargar_max_ids(self) -> None:
        """Lee MAX(id) de cada dimensión para continuar la secuencia local/escritura."""
        if not self.conn:
            return
        tablas = [
            "raiz", "escuela", "paquete", "programa", "materia", "granulo",
            "cliente", "destinatario", "periodo", "extension", "archivo",
        ]
        with self.conn.cursor() as cur:
            for tabla in tablas:
                cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {SCHEMA}.{tabla}")
                self.next_ids[tabla] = int(cur.fetchone()[0])

    def _next_id(self, tabla: str) -> int:
        """Devuelve el siguiente id local para la tabla indicada."""
        actual = self.next_ids.get(tabla, 0) + 1
        self.next_ids[tabla] = actual
        return actual

    def _lookup(self, tabla: str, where_sql: str, params: tuple) -> int | None:
        """Busca un id en Cloud SQL; None si no hay conexión o no existe la fila."""
        if not self.conn:
            return None
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT id FROM {SCHEMA}.{tabla} WHERE {where_sql}", params)
            row = cur.fetchone()
            return int(row[0]) if row else None

    def _get_or_create(self, tabla: str, key_col: str, key_val: str, extra: dict | None = None) -> int:
        """Obtiene id por clave; si no existe, crea (escritura) o asigna id local."""
        cache_key = (tabla, key_col, key_val, tuple(sorted((extra or {}).items())))
        if cache_key in self.cache:
            return self.cache[cache_key]

        found = self._lookup(tabla, f"{key_col} = %s", (key_val,))
        if found is not None:
            self.cache[cache_key] = found
            return found

        if self.conn and not self.readonly:
            # Aquí se inserta la dimensión nueva en Cloud SQL
            new_id = self._next_id(tabla)
            cols = ["id", key_col]
            vals: list[object] = [new_id, key_val]
            if extra:
                for col, val in extra.items():
                    cols.append(col)
                    vals.append(val)
            placeholders = ", ".join(["%s"] * len(cols))
            with self.conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {SCHEMA}.{tabla} ({', '.join(cols)}) VALUES ({placeholders})",
                    vals,
                )
            self.conn.commit()
            self.cache[cache_key] = new_id
            return new_id

        new_id = self._next_id(tabla)
        self.cache[cache_key] = new_id
        return new_id

    def resolver_granulo(self, materia_id: int, codigo: str, nombre: str) -> int:
        """Resuelve id de gránulo por (materia_id, codigo G+dígitos); crea si aplica."""
        key = ("granulo", materia_id, codigo)
        if key in self.cache:
            return self.cache[key]

        found = self._lookup("granulo", "materia_id = %s AND codigo = %s", (materia_id, codigo))
        if found is not None:
            self.cache[key] = found
            return found

        if self.conn and not self.readonly:
            new_id = self._next_id("granulo")
            with self.conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {SCHEMA}.granulo (id, materia_id, codigo, nombre) VALUES (%s,%s,%s,%s)",
                    (new_id, materia_id, codigo, nombre),
                )
            self.conn.commit()
            self.cache[key] = new_id
            return new_id

        new_id = self._next_id("granulo")
        self.cache[key] = new_id
        return new_id

    def resolver_materia(
        self, programa_id: int, paquete_id: int, semestre: int, nombre: str
    ) -> int:
        """Resuelve id de materia por programa+paquete+semestre+nombre; crea si aplica."""
        key = ("materia", programa_id, paquete_id, semestre, nombre)
        if key in self.cache:
            return self.cache[key]

        found = self._lookup(
            "materia",
            "programa_id=%s AND paquete_id=%s AND semestre=%s AND nombre=%s",
            (programa_id, paquete_id, semestre, nombre),
        )
        if found is not None:
            self.cache[key] = found
            return found

        if self.conn and not self.readonly:
            new_id = self._next_id("materia")
            with self.conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {SCHEMA}.materia (id, programa_id, paquete_id, semestre, nombre) VALUES (%s,%s,%s,%s,%s)",
                    (new_id, programa_id, paquete_id, semestre, nombre),
                )
            self.conn.commit()
            self.cache[key] = new_id
            return new_id

        new_id = self._next_id("materia")
        self.cache[key] = new_id
        return new_id

    def resolver_archivo(self, enlace: str) -> int | None:
        """Busca archivo_id en GCP por enlace; None si no existe o no hay DB."""
        if not enlace:
            return None
        if self.conn:
            with self.conn.cursor() as cur:
                cur.execute(f"SELECT id FROM {SCHEMA}.archivo WHERE enlace = %s", (enlace,))
                row = cur.fetchone()
                if row:
                    return int(row[0])
        return None

    def resolver_extension(self, tipo: str) -> int:
        """Resuelve extension_id: primero EXTENSION_MAP fijo, luego get_or_create."""
        tipo_norm = norm_text(tipo) if tipo else ""
        if tipo_norm in EXTENSION_MAP:
            key = ("extension", "tipo", tipo_norm)
            if key not in self.cache:
                self.cache[key] = EXTENSION_MAP[tipo_norm]
            return self.cache[key]
        return self._get_or_create("extension", "tipo", tipo_norm or "SIN_EXTENSION")

    def construir_fila(self, reg: dict, ahora: str) -> dict[str, str]:
        """Arma una fila CSV desnormalizada resolviendo todos los IDs del registro Drive."""
        raiz_id = self._get_or_create("raiz", "nombre", reg["raiz"])
        dest_id = self._get_or_create("destinatario", "codigo", reg["destinatario"])
        periodo_id = self._get_or_create("periodo", "codigo", reg["periodo"])
        cliente_id = self._get_or_create("cliente", "nombre", reg["cliente"])
        escuela_id = self._get_or_create("escuela", "nombre", reg["escuela"])
        programa_id = self._get_or_create(
            "programa", "nombre", reg["programa"], {"escuela_id": escuela_id}
        )
        paquete_id = self._get_or_create("paquete", "nombre", reg["paquete"])
        semestre = int(reg["semestre"])
        materia_id = self.resolver_materia(programa_id, paquete_id, semestre, reg["materia"])
        granulo_id = self.resolver_granulo(materia_id, reg["codigo"], reg["granulo_nombre"])
        extension_id = self.resolver_extension(reg["extension"])

        archivo_id = self.resolver_archivo(reg["archivo_enlace"])
        if archivo_id is None:
            archivo_id = self._next_id("archivo")

        return {
            "archivo_id": str(archivo_id),
            "archivo_nombre": reg["archivo_nombre"],
            "archivo_nombre_original": reg["archivo_nombre_original"],
            "archivo_enlace": reg["archivo_enlace"],
            "archivo_hash": "",
            "archivo_fecha_registro": ahora,
            "archivo_activo": "true",
            "granulo_id": str(granulo_id),
            "granulo_codigo": reg["codigo"],
            "granulo_nombre": reg["granulo_nombre"],
            "materia_id": str(materia_id),
            "materia_semestre": reg["semestre"],
            "materia_nombre": reg["materia"],
            "programa_id": str(programa_id),
            "programa_nombre": reg["programa"],
            "escuela_id": str(escuela_id),
            "escuela_nombre": reg["escuela"],
            "paquete_id": str(paquete_id),
            "paquete_nombre": reg["paquete"],
            "raiz_id": str(raiz_id),
            "raiz_nombre": raiz_nombre_display(reg["raiz"]),
            "destinatario_id": str(dest_id),
            "destinatario_codigo": reg["destinatario"],
            "periodo_id": str(periodo_id),
            "periodo_codigo": reg["periodo"],
            "cliente_id": str(cliente_id),
            "cliente_nombre": reg["cliente"],
            "extension_id": str(extension_id),
            "extension_tipo": reg["extension"],
        }

    def close(self) -> None:
        """Cierra la conexión a Cloud SQL si estaba abierta."""
        if self.conn:
            self.conn.close()


class ReferenciaGcp:
    """
    Índice de un CSV exportado de GCP (studio_results) para reutilizar filas/IDs
    ya existentes, buscando por archivo_enlace o por file ID de Drive.
    """

    def __init__(self, ruta: Path | None):
        """Carga el CSV de referencia en mapas por enlace y por file id."""
        self.por_enlace: dict[str, dict[str, str]] = {}
        self.por_id: dict[str, dict[str, str]] = {}
        if not ruta or not ruta.exists():
            return
        with ruta.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                enlace = row.get("archivo_enlace", "")
                if not enlace:
                    continue
                self.por_enlace[enlace] = row
                file_id = extraer_id_archivo(enlace)
                if file_id:
                    self.por_id[file_id] = row

    def buscar(self, enlace: str) -> dict[str, str] | None:
        """Devuelve la fila de referencia por enlace o por id de archivo Drive."""
        if enlace in self.por_enlace:
            return self.por_enlace[enlace]
        file_id = extraer_id_archivo(enlace)
        return self.por_id.get(file_id)


def generar(
    folder_id: str,
    salida: Path,
    referencia: Path | None = None,
    solo_lectura_db: bool = True,
) -> int:
    """
    Orquesta: autentica Drive → escanea → resuelve IDs (ref CSV / Cloud SQL) → escribe CSV.

    Retorna 0 si generó filas; 1 si no hubo archivos con estructura esperada.
    """
    # Aquí se construye el cliente de Drive API
    servicio = build("drive", "v3", credentials=autenticar_drive(), cache_discovery=False)
    print("Escaneando Google Drive...", flush=True)
    registros = escanear_drive(servicio, folder_id)
    print(f"Archivos G encontrados (ruta estándar): {len(registros)}")

    if not registros:
        print("No se encontraron archivos con la estructura esperada.")
        return 1

    # Aquí se preparan referencia GCP e IdResolver (esquema fabrica_pruebas por defecto)
    ref = ReferenciaGcp(referencia)
    resolver = IdResolver(readonly=solo_lectura_db)
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    filas: list[dict[str, str]] = []
    desde_ref = 0

    for idx, reg in enumerate(registros, start=1):
        if idx % 500 == 0 or idx == len(registros):
            print(f"  Resolviendo IDs {idx}/{len(registros)}...")
        enlace = reg["archivo_enlace"]
        fila_ref = ref.buscar(enlace)
        if fila_ref:
            # Aquí se reutiliza la fila ya exportada de GCP (mismos IDs)
            filas.append(fila_ref)
            desde_ref += 1
        else:
            # Aquí se construye una fila nueva resolviendo IDs en DB / locales
            filas.append(resolver.construir_fila(reg, ahora))

    resolver.close()

    # Aquí se escribe el CSV desnormalizado con COLUMNAS_SALIDA
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNAS_SALIDA, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(filas)

    print(f"Base generada: {salida}")
    print(f"Total filas: {len(filas)}")
    print(f"Desde referencia GCP: {desde_ref}")
    print(f"Nuevas filas: {len(filas) - desde_ref}")
    return 0


def parse_args() -> argparse.Namespace:
    """Define CLI: carpeta Drive, CSV de salida, CSV referencia y flag --escribir-db."""
    parser = argparse.ArgumentParser(description="Genera base LMS desnormalizada desde Google Drive.")
    parser.add_argument(
        "carpeta",
        nargs="?",
        default=f"https://drive.google.com/drive/folders/{CARPETA_DEFAULT}",
    )
    parser.add_argument(
        "-o",
        "--salida",
        default=str(BASE_DIR / "lms_base_final.csv"),
    )
    parser.add_argument(
        "--referencia",
        default=r"c:\Users\sara_martinezl\Downloads\studio_results_20260618_1055.csv",
        help="CSV exportado de GCP para reutilizar IDs existentes por enlace.",
    )
    parser.add_argument(
        "--escribir-db",
        action="store_true",
        help="Insertar dimensiones nuevas en Cloud SQL (por defecto solo lee IDs).",
    )
    return parser.parse_args()


def main() -> int:
    """Punto de entrada CLI: parsea args, genera la base y reporta errores comunes."""
    args = parse_args()
    try:
        folder_id = extraer_id_carpeta(args.carpeta)
        ref = Path(args.referencia) if args.referencia else None
        return generar(
            folder_id,
            Path(args.salida),
            referencia=ref,
            solo_lectura_db=not args.escribir_db,
        )
    except (ValueError, FileNotFoundError, HttpError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
