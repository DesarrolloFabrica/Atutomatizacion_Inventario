"""
CLONACION_CARPETA — notificar_clonacion.py
------------------------------------------
Envía el correo Gmail DESPUÉS de clonar.

Preferencia: cuerpo corto + enlace a la Google Sheet del inventario.
Si no hubo Sheet, adjunta el Excel local.
Destinatarios: CORREOS_AVISO en .env.

Lo llama clone_carpeta_drive.py al final de main(); no hace falta correrlo solo.
"""

from __future__ import annotations

import base64, html, logging, os
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def cargar_destinatarios(base: Path) -> list[str]:
    """# Aquí se leen los correos del .env (separados por coma)."""
    load_dotenv(base / ".env")
    crudo = os.getenv("CORREOS_AVISO", "")
    return [c.strip() for c in crudo.split(",") if c.strip()]


def _html_resumen(
    estado: str,
    fecha: str,
    resumenes: list[dict],
    nota_error: str,
    enlace_hoja: str = "",
) -> str:
    """
    # Aquí se arma el HTML del correo.
    Compara conteos origen vs clon y elige título/color:
      verde = OK, naranja = diferencias, rojo = error.
    """
    mas = menos = False
    lineas_conteo = []
    for r in resumenes:
        ao = r.get("archivos_origen")
        ac = r.get("archivos_clon")
        nombre = html.escape(str(r.get("destino_nombre") or r.get("etiqueta") or ""))
        if ao is not None and ac is not None:
            lineas_conteo.append(
                f"{nombre}: origen {ao} archivo(s), clon {ac} archivo(s)."
            )
            if ac > ao:
                mas = True
            if ac < ao:
                menos = True

    # Elige mensaje según el resultado de la corrida.
    if estado == "con error":
        titulo = "El proceso no terminó correctamente."
        color = "#b02a37"
    elif mas and not menos:
        titulo = (
            "La clonación terminó, pero el clon tiene MÁS archivos que el origen "
            "(duplicados). No es un proceso exitoso."
        )
        color = "#b36b00"
    elif menos and not mas:
        titulo = (
            "La clonación terminó, pero al clon le FALTAN archivos respecto al origen. "
            "No es un proceso exitoso."
        )
        color = "#b36b00"
    elif mas and menos:
        titulo = (
            "La clonación terminó con diferencias: hay archivos de más y también faltantes."
        )
        color = "#b36b00"
    elif estado == "con diferencias":
        titulo = (
            "La clonación terminó con diferencias de conteo. El detalle está en Google Sheets."
        )
        color = "#b36b00"
    else:
        titulo = "El proceso de clonación terminó de forma exitosa. Origen y clon coinciden."
        color = "#1e7e34"

    # Nombres de carpetas destino clonadas.
    destinos = ", ".join(
        html.escape(str(r.get("destino_nombre", ""))) for r in resumenes if r.get("destino_nombre")
    )
    linea_destino = f"<p>Carpeta(s) clonada(s): {destinos}.</p>" if destinos else ""

    # Links directos a Drive (si vienen en el resumen).
    links_drive = []
    for r in resumenes:
        enlace = r.get("enlace") or ""
        nombre = html.escape(str(r.get("destino_nombre", "Drive")))
        if enlace:
            links_drive.append(
                f'<a href="{html.escape(str(enlace), quote=True)}">Abrir en Drive — {nombre}</a>'
            )
    linea_drive = f"<p>{' · '.join(links_drive)}</p>" if links_drive else ""

    linea_conteo = ""
    if lineas_conteo:
        linea_conteo = "<p>" + "<br/>".join(lineas_conteo) + "</p>"
    extra = f"<p>{html.escape(nota_error)}</p>" if nota_error else ""

    # Link a la Google Sheet del inventario (lo más importante del correo).
    link_sheet = ""
    if enlace_hoja:
        link_sheet = (
            f'<p>Copia en Google Sheets: '
            f'<a href="{html.escape(enlace_hoja, quote=True)}">abrir hoja</a></p>'
        )

    return f"""
    <html><body style="font-family:Calibri,Arial,sans-serif;color:#222">
      <p style="font-size:16px;color:{color}"><b>{titulo}</b></p>
      <p>Fecha: {fecha}</p>
      {linea_conteo}
      {linea_destino}
      {linea_drive}
      {extra}
      <p>El detalle por materia (Moodle, SCORM, faltantes, etc.) está en <b>Google Sheets</b>.</p>
      {link_sheet}
    </body></html>
    """


def enviar_aviso_clonacion(
    creds: Credentials,
    destinatarios: list[str],
    estado: str,
    resumenes: list[dict],
    adjunto_excel: Path | None,
    nota_error: str = "",
    enlace_hoja: str = "",
) -> None:
    """
    # Aquí se envía el correo por Gmail API.
    Pasos: validar destinatarios → asunto → HTML → (opcional Excel) → send.
    """
    if not destinatarios:
        logger.warning("No hay CORREOS_AVISO en .env: no se envió correo.")
        print("Aviso: no hay destinatarios en .env (CORREOS_AVISO). No se envió correo.", flush=True)
        return

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Asunto según estado de la corrida.
    asunto = {
        "exitoso": "Clonación Drive: proceso exitoso (origen y clon coinciden)",
        "con diferencias": "Clonación Drive: el clon NO coincide con el origen",
        "con error": "Clonación Drive: el proceso presentó un error",
    }.get(estado, "Clonación Drive: aviso")

    # Cuerpo HTML.
    cuerpo = _html_resumen(estado, fecha, resumenes, nota_error, enlace_hoja)
    msg = MIMEMultipart()
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "html", "utf-8"))

    # Si no hay Sheet, adjunta el Excel de inventario.
    if adjunto_excel is not None and adjunto_excel.is_file():
        parte = MIMEBase(
            "application",
            "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        parte.set_payload(adjunto_excel.read_bytes())
        encoders.encode_base64(parte)
        parte.add_header("Content-Disposition", "attachment", filename=adjunto_excel.name)
        msg.attach(parte)

    # Gmail exige el mensaje en base64 URL-safe.
    crudo = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    gmail = build("gmail", "v1", credentials=creds, static_discovery=True)
    gmail.users().messages().send(userId="me", body={"raw": crudo}).execute()
    logger.info("Correo de aviso enviado a %s", destinatarios)
    print(f"Correo de aviso enviado a: {', '.join(destinatarios)}", flush=True)
