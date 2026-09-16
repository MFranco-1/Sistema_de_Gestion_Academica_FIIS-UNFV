import os
import re

import pg8000.native


db_name = os.getenv("PGDATABASE", "universidad_db")
if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", db_name):
    raise ValueError("PGDATABASE solo puede contener letras, números y guion bajo.")

# Conectar a postgres (base de datos por defecto) para crear nuestra base de datos
try:
    conn = pg8000.native.Connection(
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "postgres"),
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database="postgres",
    )

    # Comprobar si la base de datos existe
    # pg8000 requiere query con placeholders diferentes pero para una db especifica:
    rows = conn.run(
        "SELECT 1 FROM pg_catalog.pg_database WHERE datname = :nombre",
        nombre=db_name,
    )

    if not rows:
        # Commit para salir de transaccion
        conn.run("COMMIT")
        conn.run(f'CREATE DATABASE "{db_name}"')
        print(f"Base de datos '{db_name}' creada exitosamente.")
    else:
        print(f"La base de datos '{db_name}' ya existe.")

    conn.close()
except Exception as e:
    print(f"Error al conectar con postgres: {e}")
