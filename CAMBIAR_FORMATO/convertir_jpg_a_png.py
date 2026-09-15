"""
CAMBIAR_FORMATO — convertir_jpg_a_png.py
----------------------------------------
Qué hace: JPG/JPEG → PNG en una carpeta de Drive (y subcarpetas).
El JPG original va a la papelera. El PNG queda en el mismo lugar.

No usa Excel. No manda correo. No toca GCP.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------

# Bytes en memoria (descarga/subida sin guardar archivo temporal en disco).
import io

# Rutas de sistema operativo (carpeta del script, unir paths).
import os

# Expresiones regulares (cambiar .jpg/.jpeg por .png en el nombre).
import re

# Copiar/borrar archivos (guardar token.json de forma segura).
import shutil

# Carpeta temporal del sistema (evitar fallos con OneDrive).
import tempfile

# Renueva el token OAuth si expiró.
from google.auth.transport.requests import Request

# Objeto de credenciales de usuario Google.
from google.oauth2.credentials import Credentials

# Flujo “aplicación de escritorio” (abre login en el navegador).
from google_auth_oauthlib.flow import InstalledAppFlow

# Cliente de la API de Google Drive.
from googleapiclient.discovery import build

# Descargar / subir contenido binario a Drive.
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# Abrir imagen JPG y guardarla como PNG (Pillow).
from PIL import Image

# ---------------------------------------------------------------------------
# CONFIGURACIÓN (ajustar antes de correr)
# ---------------------------------------------------------------------------

# Carpeta donde está este .py.
DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# ID de la carpeta raíz en Drive donde se buscarán JPG (cámbialo al lote real).
ID_CARPETA = "1MwOPrhc-BO2ZXnF-guC2pRcU9LER_Qqa"

# OAuth Desktop (te lo da el admin). NO va al repo.
RUTA_CREDENCIALES = os.path.join(DIRECTORIO_SCRIPT, "credenciales.json")

# Sesión guardada después del primer login. Tampoco va al repo.
RUTA_TOKEN = os.path.join(DIRECTORIO_SCRIPT, "token.json")

# Permisos que se piden a Google.
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Tipos MIME que usa la API de Drive.
MIME_JPEG = "image/jpeg"
MIME_CARPETA = "application/vnd.google-apps.folder"


def guardar_token(creds):
    """Guarda token.json escribiendo primero en temp (más estable con OneDrive)."""
    # Convierte las credenciales a texto JSON.
    contenido = creds.to_json()
    # Archivo temporal fuera de OneDrive.
    ruta_tmp = os.path.join(tempfile.gettempdir(), "token_drive_tmp.json")
    with open(ruta_tmp, "w", encoding="utf-8") as archivo_tmp:
        archivo_tmp.write(contenido)
    try:
        # Si ya había token, lo borra y copia el nuevo.
        if os.path.exists(RUTA_TOKEN):
            os.remove(RUTA_TOKEN)
        shutil.copy2(ruta_tmp, RUTA_TOKEN)
    except OSError as error:
        print(
            f"Aviso: no se pudo actualizar token.json ({error}). La sesión actual sí funciona.",
            flush=True,
        )
    finally:
        # Limpia el temporal.
        try:
            os.remove(ruta_tmp)
        except OSError:
            pass


def obtener_servicio():
    """# Aquí se autentica con Google y se crea el cliente de Drive."""
    print("Iniciando autenticación con token.json...", flush=True)
    creds = None

    # Si ya existe token.json, lo carga.
    if os.path.exists(RUTA_TOKEN):
        creds = Credentials.from_authorized_user_file(RUTA_TOKEN, SCOPES)

    # Si no hay token válido…
    if not creds or not creds.valid:
        # …intenta renovarlo sin abrir el navegador…
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # …o pide login nuevo con credenciales.json.
            flujo = InstalledAppFlow.from_client_secrets_file(RUTA_CREDENCIALES, SCOPES)
            creds = flujo.run_local_server(port=0)
        guardar_token(creds)

    # Construye el servicio Drive v3 listo para listar/subir/borrar.
    servicio = build("drive", "v3", credentials=creds)
    print("Conectado a Drive.", flush=True)
    return servicio


def listar_hijos(servicio, id_carpeta, mime_type):
    """# Aquí se listan hijos de una carpeta (solo JPEG o solo carpetas)."""
    # Consulta de Drive: “hijos de esta carpeta, de este tipo, no en papelera”.
    consulta = (
        f"'{id_carpeta}' in parents and mimeType = '{mime_type}' and trashed = false"
    )
    pagina = None
    while True:
        # La API pagina de a bloques; nextPageToken pide la siguiente página.
        respuesta = (
            servicio.files()
            .list(
                q=consulta,
                spaces="drive",
                fields="nextPageToken, files(id, name)",
                pageToken=pagina,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        # Entrega cada archivo al que llama esta función (generador).
        for archivo in respuesta.get("files", []):
            yield archivo
        pagina = respuesta.get("nextPageToken")
        if not pagina:
            break


def descargar_bytes(servicio, id_archivo):
    """# Aquí se descarga el JPG a memoria (BytesIO)."""
    peticion = servicio.files().get_media(fileId=id_archivo, supportsAllDrives=True)
    buffer = io.BytesIO()
    descargador = MediaIoBaseDownload(buffer, peticion)
    listo = False
    # next_chunk descarga por partes hasta terminar.
    while not listo:
        _, listo = descargador.next_chunk()
    buffer.seek(0)
    return buffer


def convertir_a_png(buffer_jpg):
    """# Aquí Pillow abre el JPG y lo guarda como PNG en memoria."""
    imagen = Image.open(buffer_jpg)
    # Ajusta el modo de color según si tiene transparencia o no.
    if imagen.mode in ("RGBA", "P"):
        imagen = imagen.convert("RGBA")
    else:
        imagen = imagen.convert("RGB")
    buffer_png = io.BytesIO()
    imagen.save(buffer_png, format="PNG")
    buffer_png.seek(0)
    return buffer_png


def nombre_png(nombre_original):
    """# Aquí se cambia la extensión del nombre a .png."""
    return re.sub(r"\.(jpg|jpeg)$", "", nombre_original, flags=re.IGNORECASE) + ".png"


def procesar_carpeta(servicio, id_carpeta, nombre_carpeta, contadores):
    """
    # Aquí está el trabajo principal por carpeta:
    1) convertir todos los JPEG de ESTA carpeta
    2) entrar a cada subcarpeta (recursivo)
    """
    print(f"Procesando carpeta: {nombre_carpeta}", flush=True)

    # --- Paso A: cada JPEG de esta carpeta ---
    for archivo in listar_hijos(servicio, id_carpeta, MIME_JPEG):
        nombre_original = archivo["name"]
        print(f"JPEG encontrado: {nombre_original} (en carpeta: {nombre_carpeta})", flush=True)
        try:
            # Descarga → convierte → nuevo nombre.
            buffer_jpg = descargar_bytes(servicio, archivo["id"])
            buffer_png = convertir_a_png(buffer_jpg)
            nuevo_nombre = nombre_png(nombre_original)

            # Sube el PNG como archivo NUEVO en la misma carpeta.
            media = MediaIoBaseUpload(buffer_png, mimetype="image/png", resumable=False)
            servicio.files().create(
                body={
                    "name": nuevo_nombre,
                    "parents": [id_carpeta],
                    "mimeType": "image/png",
                },
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            ).execute()

            # Manda el JPG original a la papelera (no borrado permanente).
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

    # --- Paso B: bajar a subcarpetas ---
    for subcarpeta in listar_hijos(servicio, id_carpeta, MIME_CARPETA):
        procesar_carpeta(servicio, subcarpeta["id"], subcarpeta["name"], contadores)


def main():
    """# Aquí empieza el programa cuando corres: python convertir_jpg_a_png.py"""
    # 1) Login / servicio Drive.
    servicio = obtener_servicio()
    # 2) Lee el nombre de la carpeta raíz (ID_CARPETA).
    carpeta = (
        servicio.files()
        .get(fileId=ID_CARPETA, fields="id, name", supportsAllDrives=True)
        .execute()
    )
    # 3) Contadores de resultado.
    contadores = {"convertidos": 0, "errores": 0}
    # 4) Procesa el árbol completo.
    procesar_carpeta(servicio, carpeta["id"], carpeta["name"], contadores)
    # 5) Resumen final en consola.
    print(
        f"Proceso terminado. Archivos convertidos: {contadores['convertidos']}. "
        f"Errores: {contadores['errores']}",
        flush=True,
    )


# Solo corre main() si ejecutas este archivo directamente (no si lo importas).
if __name__ == "__main__":
    main()
