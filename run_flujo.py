"""
run_flujo.py — orquestador del proceso completo
----------------------------------------------
Ejecuta en serie (si un paso falla, se detiene):

  1) CAMBIAR_FORMATO / convertir_jpg_a_png.py   (obligatorio; omitir con --sin-formato)
  2) CLONACION_CARPETA / clone_carpeta_drive.py -> clonar + inventario + correo 1
  3) LMS_Fabrica / generar_base_rutas.py        -> CSV
  4) LMS_Fabrica / cargar_base_gcp.py           -> Cloud SQL + correo 2

No ejecuta clonar_esquema_pruebas.py (admin, una sola vez; fuera del flujo diario).

Uso tipico (desde la raiz del repo):

  python run_flujo.py --carpeta-formato "https://drive.google.com/drive/folders/<ID_CARPETA>"
  python run_flujo.py --excel C:\\ruta\\RUTAS.xlsx --carpeta-formato "https://drive.google.com/drive/folders/<ID_CARPETA>"
  python run_flujo.py --sin-formato --sin-clon --schema fabrica_pruebas
"""

from __future__ import annotations

import argparse, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIR_FORMATO = ROOT / "CAMBIAR_FORMATO"
DIR_CLON = ROOT / "CLONACION_CARPETA"
DIR_LMS = ROOT / "LMS_Fabrica"
CSV_DEFAULT = DIR_LMS / "lms_base_rutas.csv"

# Para importar resolver_rutas_excel desde la raíz del repo
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from rutas_excel import resolver_rutas_excel  # noqa: E402


def correr_paso(nombre: str, comando: list[str], cwd: Path) -> None:
    print("\n" + "=" * 60, flush=True)
    print(f"PASO: {nombre}", flush=True)
    print(f"CMD : {' '.join(comando)}", flush=True)
    print(f"CWD : {cwd}", flush=True)
    print("=" * 60 + "\n", flush=True)
    resultado = subprocess.run(comando, cwd=str(cwd))
    if resultado.returncode != 0:
        raise SystemExit(
            f"Flujo detenido: fallo '{nombre}' (codigo {resultado.returncode})."
        )
    print(f"\nOK: {nombre}\n", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Orquesta el flujo: formato -> clon/inventario -> CSV -> GCP."
    )
    parser.add_argument(
        "--excel",
        type=Path,
        default=None,
        help="Ruta a RUTAS.xlsx (también se puede usar la variable RUTAS_XLSX).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=CSV_DEFAULT,
        help=f"CSV intermedio (default: {CSV_DEFAULT})",
    )
    parser.add_argument(
        "--schema",
        default="fabrica_pruebas",
        help="Esquema Cloud SQL (default: fabrica_pruebas). No crea esquema.",
    )
    parser.add_argument(
        "--carpeta-formato",
        default="",
        help="Enlace o ID de la carpeta Drive para JPG→PNG (obligatorio salvo --sin-formato).",
    )
    parser.add_argument(
        "--sin-formato",
        action="store_true",
        help="Omite conversion JPG a PNG (por defecto SI se ejecuta).",
    )
    parser.add_argument(
        "--sin-clon",
        action="store_true",
        help="Omite clonacion (solo CSV + carga GCP).",
    )
    parser.add_argument(
        "--sin-gcp",
        action="store_true",
        help="Omite generacion CSV y carga GCP (solo formato / clon).",
    )
    parser.add_argument(
        "--sin-correo",
        action="store_true",
        help="Pasa --sin-correo a cargar_base_gcp.py.",
    )
    parser.add_argument(
        "--actualizar",
        action="store_true",
        help="Pasa --actualizar a cargar_base_gcp.py (solo pruebas).",
    )
    # Compatibilidad: --con-formato ya no es necesario (formato va por defecto).
    parser.add_argument(
        "--con-formato",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    csv_out = args.csv.resolve()
    py = sys.executable

    try:
        excel = resolver_rutas_excel(args.excel, ROOT, DIR_CLON, DIR_LMS)
    except FileNotFoundError as err:
        if not args.sin_clon or not args.sin_gcp:
            print(str(err), file=sys.stderr)
            return 1
        excel = Path("RUTAS.xlsx")

    print("Flujo continuo Automatizacion Inventario", flush=True)
    print(f"  Excel : {excel}", flush=True)
    print(f"  CSV   : {csv_out}", flush=True)
    print(f"  Schema: {args.schema}", flush=True)
    print("  (No se ejecuta creacion/clonacion de esquema DB)", flush=True)

    if not args.sin_formato:
        carpeta = (args.carpeta_formato or "").strip()
        if not carpeta:
            print(
                "Error: JPG→PNG es obligatorio. Indica la carpeta con "
                "--carpeta-formato (enlace o ID de Drive), "
                "o usa --sin-formato solo si el lote ya está en PNG.",
                file=sys.stderr,
            )
            return 1
        correr_paso(
            "Formato JPG a PNG",
            [py, "convertir_jpg_a_png.py", "--carpeta", carpeta],
            DIR_FORMATO,
        )

    if not args.sin_clon:
        # Orden operativo: primero clonar (crea destino), luego inventario compara origen vs destino.
        correr_paso(
            "Clonacion + inventario + correo 1",
            [py, "clone_carpeta_drive.py", "--excel", str(excel)],
            DIR_CLON,
        )

    if not args.sin_gcp:
        if not excel.is_file():
            print(f"No se encontro el Excel: {excel}", file=sys.stderr)
            return 1
        correr_paso(
            "Generar CSV desde destino Drive",
            [py, "generar_base_rutas.py", "--excel", str(excel), "-o", str(csv_out)],
            DIR_LMS,
        )
        cmd_gcp = [
            py,
            "cargar_base_gcp.py",
            "-i",
            str(csv_out),
            "--schema",
            args.schema,
        ]
        if args.sin_correo:
            cmd_gcp.append("--sin-correo")
        if args.actualizar:
            cmd_gcp.append("--actualizar")
        correr_paso("Cargar Cloud SQL + correo 2", cmd_gcp, DIR_LMS)

    print("\n" + "=" * 60, flush=True)
    print("FLUJO COMPLETO: OK", flush=True)
    print("Siguiente: marcar CHECKLIST_ENTREGA.md", flush=True)
    print("=" * 60, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
