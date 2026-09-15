"""
LMS_Fabrica — clonar_esquema_pruebas.py
---------------------------------------
⚠️  USO EXCEPCIONAL DE ADMINISTRACIÓN — NO ES FLUJO DIARIO.

Qué es:
  Script de admin para crear UNA SOLA VEZ el esquema temporal
  ``fabrica_pruebas`` (o el nombre que pases con --destino), clonando
  estructura + datos desde el esquema productivo ``fabrica``.

Qué NO es:
  - No forma parte del flujo diario de carga LMS.
  - No lo ejecutes en cada lote ni en cada corrida de prueba.
  - No sustituye a cargar_base_gcp.py / generar_base_rutas.py.

Regla de oro:
  El esquema de pruebas se crea UNA vez. Después solo cargas datos
  de prueba apuntando a ese esquema. Si el destino ya tiene tablas,
  este script ABORTA sin borrar nada.

Qué hace (solo copia; nunca borra ``fabrica``):
  CREATE SCHEMA + tablas + secuencias + defaults + FKs + funciones
  + vistas + triggers, y verifica conteos fila a fila.

Requiere: .env de Cloud SQL (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

from generar_base_lms import BASE_DIR, ENV_PATH

# Esquema productivo (origen). Solo se lee; nunca se modifica.
SOURCE_DEFAULT = "fabrica"
# Esquema temporal de pruebas (destino). Se crea una vez y se reutiliza.
DESTINO_DEFAULT = "fabrica_pruebas"
# Solo nombres SQL seguros (minúsculas, guión bajo, dígitos).
IDENT_OK = re.compile(r"^[a-z_][a-z0-9_]*$")

# Orden de búsqueda del .env: carpeta local → ruta del módulo → carpeta hermana.
CANDIDATOS_ENV = [
    BASE_DIR / ".env",
    ENV_PATH,
    BASE_DIR.parent / "CARGA_LMS_GCP_INV" / ".env",
]


def validar_identificador(nombre: str, etiqueta: str) -> str:
    """
    Normaliza y valida un nombre de esquema PostgreSQL.
    Evita inyección / identificadores raros antes de armar SQL.
    """
    valor = (nombre or "").strip().lower()
    if not IDENT_OK.fullmatch(valor):
        raise ValueError(f"{etiqueta} no válido: {nombre!r}")
    return valor


def resolver_env_path() -> Path:
    """
    Elige el primer .env que exista entre los candidatos.
    Si ninguno existe, devuelve ENV_PATH (para el mensaje de error).
    """
    for ruta in CANDIDATOS_ENV:
        if ruta.exists():
            return ruta
    return ENV_PATH


def conectar():
    """
    Abre conexión a Cloud SQL / Postgres con las variables del .env.
    Exige DB_PASSWORD; el resto sale de DB_HOST, DB_PORT, DB_NAME, DB_USER.
    """
    env_path = resolver_env_path()
    if not env_path.exists():
        raise FileNotFoundError(
            f"No se encontró {env_path}. Coloca el .env de Cloud SQL ahí "
            f"o en {BASE_DIR / '.env'}."
        )
    load_dotenv(env_path)
    password = os.getenv("DB_PASSWORD", "")
    if not password:
        raise ValueError("DB_PASSWORD no configurada en .env")
    print(f"Usando credenciales: {env_path}")
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=password,
        connect_timeout=30,
    )


def q_ident(*partes: str):
    """Arma un identificador SQL seguro tipo esquema.tabla (psycopg2.sql)."""
    return sql.SQL(".").join(sql.Identifier(p) for p in partes)


def esquema_existe(cur, nombre: str) -> bool:
    """True si el esquema ya existe en el catálogo de Postgres."""
    cur.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", (nombre,))
    return cur.fetchone() is not None


def tablas_del_esquema(cur, esquema: str) -> list[str]:
    """Lista nombres de tablas reales (relkind = 'r') del esquema."""
    cur.execute(
        """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s
          AND c.relkind = 'r'
        ORDER BY c.relname
        """,
        (esquema,),
    )
    return [row[0] for row in cur.fetchall()]


def secuencias_del_esquema(cur, esquema: str) -> list[str]:
    """Lista secuencias (relkind = 'S') del esquema."""
    cur.execute(
        """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s
          AND c.relkind = 'S'
        ORDER BY c.relname
        """,
        (esquema,),
    )
    return [row[0] for row in cur.fetchall()]


def vistas_del_esquema(cur, esquema: str) -> list[tuple[str, str]]:
    """Devuelve (nombre, definición SQL) de cada vista del esquema."""
    cur.execute(
        """
        SELECT c.relname, pg_get_viewdef(c.oid, true)
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s
          AND c.relkind = 'v'
        ORDER BY c.relname
        """,
        (esquema,),
    )
    return [(row[0], row[1]) for row in cur.fetchall()]


def contar_filas(cur, esquema: str, tabla: str) -> int:
    """COUNT(*) de una tabla (usado en verificación origen vs destino)."""
    cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(q_ident(esquema, tabla)))
    return int(cur.fetchone()[0])


def copiar_secuencias(cur, origen: str, destino: str) -> int:
    """
    Crea en destino las secuencias que falten y copia last_value / is_called.
    Si ya existe la secuencia en destino, la deja (no la recrea).
    """
    nombres = secuencias_del_esquema(cur, origen)
    copiadas = 0
    existentes = set(secuencias_del_esquema(cur, destino))
    for nombre in nombres:
        if nombre in existentes:
            continue
        cur.execute(
            sql.SQL("CREATE SEQUENCE {}").format(q_ident(destino, nombre))
        )
        cur.execute(
            sql.SQL("SELECT last_value, is_called FROM {}").format(
                q_ident(origen, nombre)
            )
        )
        last_value, is_called = cur.fetchone()
        cur.execute(
            "SELECT setval(%s, %s, %s)",
            (f"{destino}.{nombre}", int(last_value), bool(is_called)),
        )
        copiadas += 1
        existentes.add(nombre)
    return copiadas


def tabla_tiene_identity(cur, esquema: str, tabla: str) -> bool:
    """
    True si alguna columna es GENERATED ... AS IDENTITY.
    Entonces el INSERT debe usar OVERRIDING SYSTEM VALUE.
    """
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
              AND c.relname = %s
              AND a.attnum > 0
              AND NOT a.attisdropped
              AND a.attidentity <> ''
        )
        """,
        (esquema, tabla),
    )
    return bool(cur.fetchone()[0])


def copiar_tablas(cur, origen: str, destino: str) -> list[str]:
    """
    Por cada tabla de origen:
      1) CREATE TABLE ... (LIKE origen INCLUDING ALL)  → misma estructura
      2) INSERT ... SELECT *                           → mismos datos
    No toca el origen. Devuelve la lista de tablas copiadas.
    """
    tablas = tablas_del_esquema(cur, origen)
    for tabla in tablas:
        print(f"  Tabla {tabla}: creando estructura...", flush=True)
        cur.execute(
            sql.SQL("CREATE TABLE {} (LIKE {} INCLUDING ALL)").format(
                q_ident(destino, tabla),
                q_ident(origen, tabla),
            )
        )
        print(f"  Tabla {tabla}: copiando datos...", flush=True)
        if tabla_tiene_identity(cur, destino, tabla):
            insert_sql = sql.SQL(
                "INSERT INTO {} OVERRIDING SYSTEM VALUE SELECT * FROM {}"
            )
        else:
            insert_sql = sql.SQL("INSERT INTO {} SELECT * FROM {}")
        cur.execute(insert_sql.format(q_ident(destino, tabla), q_ident(origen, tabla)))
        n = contar_filas(cur, destino, tabla)
        print(f"  Tabla {tabla}: {n} filas", flush=True)
    return tablas


def reescribir_defaults(cur, origen: str, destino: str, tablas: list[str]) -> int:
    """
    Los DEFAULT suelen apuntar a secuencias de ``fabrica.*``.
    Aquí se reescriben a ``fabrica_pruebas.*`` para que las pruebas
    no consuman secuencias del esquema productivo.
    """
    cambiados = 0
    for tabla in tablas:
        cur.execute(
            """
            SELECT a.attname, pg_get_expr(d.adbin, d.adrelid)
            FROM pg_attrdef d
            JOIN pg_attribute a ON a.attrelid = d.adrelid AND a.attnum = d.adnum
            JOIN pg_class c ON c.oid = d.adrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relname = %s
            """,
            (destino, tabla),
        )
        for columna, expr in cur.fetchall():
            if not expr or f"{origen}." not in expr:
                continue
            nueva = expr.replace(f"{origen}.", f"{destino}.")
            cur.execute(
                sql.SQL("ALTER TABLE {} ALTER COLUMN {} SET DEFAULT {}").format(
                    q_ident(destino, tabla),
                    sql.Identifier(columna),
                    sql.SQL(nueva),
                )
            )
            cambiados += 1
    return cambiados


def recrear_foreign_keys(cur, origen: str, destino: str) -> int:
    """
    LIKE ... INCLUDING ALL no siempre deja las FK apuntando al destino.
    Se leen las FK del origen y se recrean en destino con el esquema corregido.
    """
    cur.execute(
        """
        SELECT
            src.relname AS table_name,
            con.conname,
            pg_get_constraintdef(con.oid)
        FROM pg_constraint con
        JOIN pg_class src ON src.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = src.relnamespace
        WHERE n.nspname = %s
          AND con.contype = 'f'
        ORDER BY src.relname, con.conname
        """,
        (origen,),
    )
    creadas = 0
    for table_name, conname, definicion in cur.fetchall():
        definicion_dest = definicion.replace(f"{origen}.", f"{destino}.")
        cur.execute(
            sql.SQL("ALTER TABLE {} ADD CONSTRAINT {} {}").format(
                q_ident(destino, table_name),
                sql.Identifier(conname),
                sql.SQL(definicion_dest),
            )
        )
        creadas += 1
    return creadas


def sincronizar_secuencias_tablas(cur, destino: str, tablas: list[str]) -> None:
    """
    Ajusta setval de cada secuencia / identity al MAX(columna) actual,
    para que el próximo INSERT no choque con PKs ya copiadas.
    """
    for tabla in tablas:
        cur.execute(
            """
            SELECT a.attname
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
              AND c.relname = %s
              AND a.attnum > 0
              AND NOT a.attisdropped
              AND (
                    a.attidentity <> ''
                    OR pg_get_serial_sequence(n.nspname || '.' || c.relname, a.attname) IS NOT NULL
                  )
            """,
            (destino, tabla),
        )
        for (columna,) in cur.fetchall():
            qualified = f"{destino}.{tabla}"
            cur.execute("SELECT pg_get_serial_sequence(%s, %s)", (qualified, columna))
            seq = cur.fetchone()[0]
            if not seq:
                continue
            cur.execute(
                sql.SQL("SELECT COALESCE(MAX({}), 1) FROM {}").format(
                    sql.Identifier(columna),
                    q_ident(destino, tabla),
                )
            )
            max_id = int(cur.fetchone()[0])
            cur.execute("SELECT setval(%s, %s, true)", (seq, max_id))


def copiar_funciones(cur, origen: str, destino: str) -> int:
    """
    Copia funciones/procedimientos SQL o PL/pgSQL del origen al destino,
    reescribiendo referencias de esquema. Omite las que vienen de extensiones.
    """
    cur.execute(
        """
        SELECT p.proname, pg_get_functiondef(p.oid)
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_language l ON l.oid = p.prolang
        WHERE n.nspname = %s
          AND p.prokind IN ('f', 'p', 'w')
          AND l.lanname IN ('sql', 'plpgsql')
          AND NOT EXISTS (
              SELECT 1
              FROM pg_depend d
              JOIN pg_extension e ON e.oid = d.refobjid
              WHERE d.objid = p.oid
                AND d.deptype = 'e'
          )
        ORDER BY p.oid
        """,
        (origen,),
    )
    copiadas = 0
    for nombre, definicion in cur.fetchall():
        definicion_dest = definicion.replace(f"{origen}.", f"{destino}.")
        print(f"  Función {nombre}...", flush=True)
        cur.execute(definicion_dest)
        copiadas += 1
    return copiadas


def copiar_vistas(cur, origen: str, destino: str) -> int:
    """Crea en destino las mismas vistas, con el SQL apuntando al esquema de prueba."""
    vistas = vistas_del_esquema(cur, origen)
    for nombre, definicion in vistas:
        definicion_dest = definicion.replace(f"{origen}.", f"{destino}.")
        cur.execute(
            sql.SQL("CREATE VIEW {} AS {}").format(
                q_ident(destino, nombre),
                sql.SQL(definicion_dest),
            )
        )
    return len(vistas)


def copiar_triggers(cur, origen: str, destino: str) -> int:
    """Recrea triggers de usuario (no internos) en el esquema destino."""
    cur.execute(
        """
        SELECT pg_get_triggerdef(t.oid)
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s
          AND NOT t.tgisinternal
        ORDER BY c.relname, t.tgname
        """,
        (origen,),
    )
    creados = 0
    for (definicion,) in cur.fetchall():
        definicion_dest = definicion.replace(f"{origen}.", f"{destino}.")
        cur.execute(definicion_dest)
        creados += 1
    return creados


def verificar(cur, origen: str, destino: str, tablas: list[str]) -> bool:
    """
    Compara COUNT(*) de cada tabla origen vs destino.
    Si alguna difiere, clonar() hará rollback (no deja clon a medias).
    """
    ok = True
    print("\nVerificación de conteos:")
    for tabla in tablas:
        n_origen = contar_filas(cur, origen, tabla)
        n_destino = contar_filas(cur, destino, tabla)
        marca = "OK" if n_origen == n_destino else "DIFF"
        if n_origen != n_destino:
            ok = False
        print(f"  [{marca}] {tabla}: fabrica={n_origen}  {destino}={n_destino}")
    return ok


def clonar(origen: str, destino: str) -> int:
    """
    Orquestación de la clonación (UNA vez, uso admin).

    Pasos:
      1) Validar nombres; origen debe ser ``fabrica``.
      2) Si destino ya tiene tablas → abortar (no borra nada).
      3) CREATE SCHEMA si hace falta.
      4) Copiar tablas, secuencias, defaults, FKs, funciones, vistas, triggers.
      5) Verificar conteos; si fallan → rollback completo.

    Devuelve 0 si todo salió bien.
    """
    origen = validar_identificador(origen, "Esquema origen")
    destino = validar_identificador(destino, "Esquema destino")
    if destino == origen:
        raise ValueError("El destino no puede ser el mismo que el origen.")
    if origen != "fabrica":
        raise ValueError("Este script solo clona el esquema fabrica (no se toca otro origen).")

    print("=" * 60)
    print("CLONACIÓN DE ESQUEMA — solo copia, no borra")
    print(f"  Origen : {origen}  (intacto)")
    print(f"  Destino: {destino}  (temporal de pruebas)")
    print("=" * 60)

    conn = conectar()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            if not esquema_existe(cur, origen):
                raise RuntimeError(f"No existe el esquema origen {origen}.")

            # Seguridad: si el destino ya tiene tablas, no tocamos nada.
            if esquema_existe(cur, destino):
                existentes = tablas_del_esquema(cur, destino)
                if existentes:
                    raise RuntimeError(
                        f"El esquema {destino} ya existe y tiene tablas "
                        f"({len(existentes)}). No se borra nada. "
                        "Usa otro --destino o elimina ese esquema tú misma."
                    )
                print(f"El esquema {destino} ya existía vacío; se reutiliza.")
            else:
                cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(destino)))
                print(f"Esquema creado: {destino}")

            # Objetos sin esquema cualificado se resuelven en el destino.
            cur.execute(
                "SELECT set_config('search_path', %s, true)",
                (f"{destino}, pg_catalog",),
            )

            tablas = copiar_tablas(cur, origen, destino)
            print(f"Tablas copiadas: {len(tablas)}")

            n_seq = copiar_secuencias(cur, origen, destino)
            print(f"Secuencias copiadas: {n_seq}")

            n_def = reescribir_defaults(cur, origen, destino, tablas)
            print(f"Defaults redirigidos al esquema de prueba: {n_def}")

            n_fk = recrear_foreign_keys(cur, origen, destino)
            print(f"Foreign keys recreadas: {n_fk}")

            sincronizar_secuencias_tablas(cur, destino, tablas)
            n_fn = copiar_funciones(cur, origen, destino)
            print(f"Funciones copiadas: {n_fn}")
            n_views = copiar_vistas(cur, origen, destino)
            print(f"Vistas copiadas: {n_views}")
            n_trg = copiar_triggers(cur, origen, destino)
            print(f"Triggers copiados: {n_trg}")

            if not verificar(cur, origen, destino, tablas):
                raise RuntimeError("Los conteos no coinciden. Se revierte la clonación.")

        conn.commit()
        print(f"\nListo. Esquema temporal: {destino}")
        print(f"El esquema {origen} no fue modificado.")
        print("\nPara cargar datos de prueba:")
        print(f"  python cargar_base_gcp.py -i lms_base_rutas.csv --schema {destino}")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    """CLI mínima: solo --destino (default fabrica_pruebas). Origen fijo: fabrica."""
    parser = argparse.ArgumentParser(
        description=(
            "USO EXCEPCIONAL (admin): clona fabrica a un esquema temporal "
            "UNA vez. No es flujo diario; no borra nada."
        )
    )
    parser.add_argument(
        "--destino",
        default=DESTINO_DEFAULT,
        help=f"Nombre del esquema temporal (default: {DESTINO_DEFAULT}).",
    )
    return parser.parse_args()


def main() -> int:
    """Punto de entrada: parsea args y llama a clonar(). Código de salida 0/1."""
    args = parse_args()
    try:
        return clonar(SOURCE_DEFAULT, args.destino)
    except (FileNotFoundError, ValueError, RuntimeError, psycopg2.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
