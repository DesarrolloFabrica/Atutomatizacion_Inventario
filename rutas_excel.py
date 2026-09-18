"""Utilidad compartida: localizar RUTAS.xlsx sin rutas de usuario fijas."""

from __future__ import annotations

import os
from pathlib import Path


def resolver_rutas_excel(
    explicit: Path | None = None,
    *extra_dirs: Path,
) -> Path:
    """
    Resuelve la ruta a RUTAS.xlsx.
    Orden: argumento --excel, variable RUTAS_XLSX, carpetas candidatas, cwd.
    """
    if explicit is not None:
        ruta = Path(explicit).expanduser().resolve()
        if ruta.is_file():
            return ruta
        raise FileNotFoundError(f"No se encontró el Excel: {ruta}")

    env = (os.getenv("RUTAS_XLSX") or "").strip()
    candidatos: list[Path] = []
    if env:
        candidatos.append(Path(env).expanduser())
    for d in extra_dirs:
        candidatos.append(Path(d) / "RUTAS.xlsx")
    candidatos.append(Path.cwd() / "RUTAS.xlsx")

    vistos: set[Path] = set()
    for c in candidatos:
        try:
            res = c.resolve()
        except OSError:
            continue
        if res in vistos:
            continue
        vistos.add(res)
        if res.is_file():
            return res

    raise FileNotFoundError(
        "No se encontró RUTAS.xlsx. Indica la ruta con --excel "
        "o define la variable de entorno RUTAS_XLSX."
    )
