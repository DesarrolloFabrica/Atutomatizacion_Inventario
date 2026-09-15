"""
run_flujo.py - orquestador continuo del proceso completo
------------------------------------------------------
Ejecuta en serie (si un paso falla, se detiene):

  1) (opcional) CAMBIAR_FORMATO / convertir_jpg_a_png.py
  2) CLONACION_CARPETA / clone_carpeta_drive.py   -> inventario + correo 1
  3) LMS_Fabrica / generar_base_rutas.py         -> CSV
  4) LMS_Fabrica / cargar_base_gcp.py            -> Cloud SQL + correo 2

No ejecuta clonar_esquema_pruebas.py (eso es admin, fuera del flujo diario).

Uso tipico (desde la raiz del repo):

  python run_flujo.py
  python run_flujo.py --con-formato
  python run_flujo.py --excel C:\\Users\\angie_vera\\Downloads\\RUTAS.xlsx
  python run_flujo.py --sin-clon --schema fabrica_pruebas
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIR_FORMATO = ROOT / "CAMBIAR_FORMATO"
DIR_CLON = ROOT / "CLONACION_CARPETA"
DIR_LMS = ROOT / "LMS_Fabrica"

# Misma ruta por defecto que usa el bloque de clonacion.
RUTAS_DEFAULT = Path(r"C:\Users\angie_vera\Downloads\RUTAS.xlsx")
CSV_DEFAULT = DIR_LMS / "lms_base_rutas.csv"


def correr_paso(nombre: str, comando: list[str], cwd: Path) -> None:
    """Lanza un subproceso; si falla, aborta el flujo completo."""
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
        description="Orquesta el flujo continuo: formato -> clon -> CSV -> GCP."
    )
    parser.add_argument(
        "--excel",
        type=Path,
        default=RUTAS_DEFAULT,
        help=f"RUTAS.xlsx (default: {RUTAS_DEFAULT})",
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
        "--con-formato",
        action="store_true",
        help="Incluye conversion JPG a PNG antes del clon.",
    )
    parser.add_argument(
        "--sin-clon",
        action="store_true",
        help="Omite clonacion (solo CSV + carga GCP).",
    )
    parser.add_argument(
        "--sin-gcp",
        action="store_true",
        help="Omite generacion CSV y carga GCP (solo clon / formato).",
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
    args = parser.parse_args(argv)

    excel = args.excel.resolve()
    csv_out = args.csv.resolve()
    py = sys.executable

    if not excel.is_file() and not args.sin_clon:
        print(f"No se encontro el Excel: {excel}", file=sys.stderr)
        return 1

    print("Flujo continuo Automatizacion Inventario", flush=True)
    print(f"  Excel : {excel}", flush=True)
    print(f"  CSV   : {csv_out}", flush=True)
    print(f"  Schema: {args.schema}", flush=True)
    print("  (No se ejecuta creacion/clonacion de esquema DB)", flush=True)

    if args.con_formato:
        correr_paso(
            "Formato JPG a PNG",
            [py, "convertir_jpg_a_png.py"],
            DIR_FORMATO,
        )

    if not args.sin_clon:
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
