"""
CLONACION_CARPETA � renovar_token.py
------------------------------------
Herramienta de mantenimiento (NO clona ni carga GCP).

Qu� hace: vuelve a autorizar OAuth y regenera token.json
usando credentials.json (aplicaci�n de escritorio).

Cu�ndo usarlo:
  - token.json no existe
  - token caduc� / fue revocado
  - falta el permiso de Gmail (correo) o Sheets

Permisos pedidos: Drive + Sheets + Gmail send
(igual que clone_carpeta_drive.py).
"""

# Tipos modernos.
from __future__ import annotations

# Rutas del directorio actual.
from pathlib import Path

# Flujo OAuth �Desktop app� de Google (abre URL en el navegador).
from google_auth_oauthlib.flow import InstalledAppFlow

# Misma lista de permisos que el clon (para que el token sirva para todo).
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
]

# Carpeta de este script.
BASE = Path(__file__).resolve().parent
# OAuth Desktop (NO subir a Git).
CREDENTIALS_PATH = BASE / "credentials.json"
# Sesi�n que se crea/actualiza aqu� (NO subir a Git).
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
