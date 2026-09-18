"""
CLONACION_CARPETA — renovar_token.py
------------------------------------
Herramienta de mantenimiento: vuelve a autorizar OAuth y regenera token.json
usando credentials.json (aplicación de escritorio).

Cuándo usarlo: token ausente, caducado/revocado, o falta permiso Gmail/Sheets.
Permisos: Drive + Sheets + Gmail send (igual que clone_carpeta_drive.py).
"""

from __future__ import annotations

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
]

BASE = Path(__file__).resolve().parent
CREDENTIALS_PATH = BASE / "credentials.json"
TOKEN_PATH = BASE / "token.json"


def main() -> None:
    """# Aqu� se hace el login y se guarda token.json."""
    # Sin credentials.json no se puede autorizar.
    if not CREDENTIALS_PATH.is_file():
        raise SystemExit(f"Falta {CREDENTIALS_PATH}")

    print(
        "Copie la URL y �brala en el navegador donde ya est� la cuenta de Drive (f�brica).",
        flush=True,
    )

    # Carga el client_id/client_secret y prepara el login.
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)

    # No abre el navegador solo: imprime la URL para pegarla en la cuenta correcta.
    creds = flow.run_local_server(
        port=0,
        open_browser=False,
        authorization_prompt_message="Abra esta URL en ese navegador:\n{url}\n",
    )

    # Guarda la sesi�n para que clone_carpeta_drive.py no pida login cada vez.
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    print(f"Guardado: {TOKEN_PATH}")


if __name__ == "__main__":
    main()
