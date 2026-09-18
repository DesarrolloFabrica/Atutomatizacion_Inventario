"""
CAMBIAR_FORMATO — convertir_jpg_a_png.py
----------------------------------------
JPG/JPEG → PNG en una carpeta de Drive (y subcarpetas).
El JPG original va a la papelera. El PNG queda en el mismo lugar.

No usa Excel. No manda correo. No toca GCP.

Uso:
  python convertir_jpg_a_png.py --carpeta "https://drive.google.com/drive/folders/<ID_CARPETA>"
"""

from __future__ import annotations

import argparse
import io
import os
import re
import shutil
import tempfile
from urllib.parse import parse_qs, urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from PIL import Image

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
RUTA_CREDENCIALES = os.path.join(DIRECTORIO_SCRIPT, "credenciales.json")
RUTA_TOKEN = os.path.join(DIRECTORIO_SCRIPT, "token.json")
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
MIME_JPEG = "image/jpeg"
MIME_CARPETA = "application/vnd.google-apps.folder"
DRIVE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def extraer_id_carpeta(entrada: str) -> str:
    """Obtiene el ID de carpeta de Drive a partir del enlace o del ID."""
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
        raise ValueError(f"No se pudo leer el ID de carpeta desde: {entrada}")
    if DRIVE_ID_PATTERN.fullmatch(texto):
        return texto
    raise ValueError(
        f"Valor no válido. Usa el enlace de la carpeta en Drive o su ID: {entrada}"
    )


def guardar_token(creds) -> None:
    contenido = creds.to_json()
    ruta_tmp = os.path.join(tempfile.gettempdir(), "token_drive_tmp.json")
    with open(ruta_tmp, "w", encoding="utf-8") as archivo_tmp:
        archivo_tmp.write(contenido)
    try:
        if os.path.exists(RUTA_TOKEN):
            os.remove(RUTA_TOKEN)
        shutil.copy2(ruta_tmp, RUTA_TOKEN)
    except OSError as error:
        print(
            f"Aviso: no se pudo actualizar token.json ({error}). La sesión actual sí funciona.",
            flush=True,
        )
    finally:
        try:
            os.remove(ruta_tmp)
        except OSError:
            pass


def obtener_servicio():
    print("Iniciando autenticación con token.json...", flush=True)
    creds = None
    if os.path.exists(RUTA_TOKEN):
        creds = Credentials.from_authorized_user_file(RUTA_TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flujo = InstalledAppFlow.from_client_secrets_file(RUTA_CREDENCIALES, SCOPES)
            creds = flujo.run_local_server(port=0)
        guardar_token(creds)
    servicio = build("drive", "v3", credentials=creds)
    print("Conectado a Drive.", flush=True)
    return servicio


def listar_hijos(servicio, id_carpeta, mime_type):
    consulta = (
        f"'{id_carpeta}' in parents and mimeType = '{mime_type}' and trashed = false"
    )
    resultados = []
    token = None
    while True:
        respuesta = (
            servicio.files()
            .list(
                q=consulta,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=1000,
            )
            .execute()
        )
        resultados.extend(respuesta.get("files", []))
        token = respuesta.get("nextPageToken")
        if not token:
            break
    return resultados


def procesar_carpeta(servicio, id_carpeta, nombre_carpeta, contadores):
    for archivo in listar_hijos(servicio, id_carpeta, MIME_JPEG):
        nombre_original = archivo["name"]
        try:
            buffer = io.BytesIO()
            request = servicio.files().get_media(
                fileId=archivo["id"], supportsAllDrives=True
            )
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            buffer.seek(0)
            with Image.open(buffer) as imagen:
                salida = io.BytesIO()
                imagen.save(salida, format="PNG")
                salida.seek(0)
            nuevo_nombre = re.sub(
                r"\.(jpe?g)$", ".png", nombre_original, flags=re.IGNORECASE
            )
            if nuevo_nombre == nombre_original:
                nuevo_nombre = f"{nombre_original}.png"
            media = MediaIoBaseUpload(salida, mimetype="image/png", resumable=True)
            servicio.files().create(
                body={
                    "name": nuevo_nombre,
                    "parents": [id_carpeta],
                    "mimeType": "image/png",
                },
                media_body=media,
                supportsAllDrives=True,
                fields="id",
            ).execute()
            servicio.files().update(
                fileId=archivo["id"],
                body={"trashed": True},
                supportsAllDrives=True,
            ).execute()
            contadores["convertidos"] += 1
            print(
                f"Convertido: {nombre_original} -> {nuevo_nombre} "
                f"(en carpeta: {nombre_carpeta})",
                flush=True,
            )
        except Exception as error:
            contadores["errores"] += 1
            print(f"Error al convertir {nombre_original}: {error}", flush=True)

    for subcarpeta in listar_hijos(servicio, id_carpeta, MIME_CARPETA):
        procesar_carpeta(servicio, subcarpeta["id"], subcarpeta["name"], contadores)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convierte JPG/JPEG a PNG en una carpeta de Google Drive."
    )
    parser.add_argument(
        "--carpeta",
        required=True,
        help="Enlace o ID de la carpeta de Google Drive a procesar.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        folder_id = extraer_id_carpeta(args.carpeta)
    except ValueError as err:
        print(f"Error: {err}", flush=True)
        return 1

    servicio = obtener_servicio()
    carpeta = (
        servicio.files()
        .get(fileId=folder_id, fields="id, name", supportsAllDrives=True)
        .execute()
    )
    contadores = {"convertidos": 0, "errores": 0}
    procesar_carpeta(servicio, carpeta["id"], carpeta["name"], contadores)
    print(
        f"Proceso terminado. Archivos convertidos: {contadores['convertidos']}. "
        f"Errores: {contadores['errores']}",
        flush=True,
    )
    return 0 if contadores["errores"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
