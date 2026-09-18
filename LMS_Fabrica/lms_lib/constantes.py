"""
Constantes compartidas del flujo LMS (sin lógica de ejecución).
Usar vía: from lms_lib.constantes import CLIENTES_VALIDOS, EXTENSION_MAP, ...
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_PATH = BASE_DIR / "token.json"
CREDENTIALS_PATH = BASE_DIR / "credenciales.json"
_ENV_CANDIDATES = [
    BASE_DIR / ".env",
    BASE_DIR.parent / "CARGA_LMS_GCP_INV" / ".env",
]
ENV_PATH = next((p for p in _ENV_CANDIDATES if p.exists()), _ENV_CANDIDATES[0])
load_dotenv(ENV_PATH)

CLIENTES_VALIDOS = {"PRODUCTO", "TANIA", "LMS_CORRECCIONES"}
PAQUETES_VALIDOS = {"MODELO_NOTEBOOK", "NOTEBOOK", "MODELO_NOTEBOOK "}
RAIZ_DISPLAY = {"LMS_CARGA": "LMS_Carga"}
SCHEMA = os.getenv("LMS_SCHEMA", "fabrica_pruebas")

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
]
MIME_FOLDER = "application/vnd.google-apps.folder"
DRIVE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
PATRON_ARCHIVO = re.compile(r"^G(\d+)(?:[_\s].*)?$", re.IGNORECASE)
PATRON_CODIGO = re.compile(r"^G(\d+)", re.IGNORECASE)
PATRON_GRANULO_NOMBRE = re.compile(r"^(G\d+)_(.+)$", re.IGNORECASE)

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

EXTENSION_MAP = {
    "mp3": 1,
    "mp4": 2,
    "pdf": 3,
    "png": 5,
    "gif": 665,
    "zip": 671,
}
