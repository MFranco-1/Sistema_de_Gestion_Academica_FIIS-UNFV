import json

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


PERMISSION_NAMES = {
    "GESTION_CURRICULAR": "Gestión curricular",
    "PLANA_DOCENTE": "Plana docente",
    "MANTENIMIENTO_ACADEMICO": "Mantenimiento académico",
    "GESTION_ESTUDIANTES": "Gestión de estudiantes",
    "GESTION_USUARIOS": "Gestión de usuarios",
    "GESTION_PERFILES": "Gestión de perfiles",
    "MATRICULA_PROPIA": "Matrícula propia",
    "GESTION_MATRICULAS": "Gestión de matrículas",
}


def _has_column(connection, table: str, column: str) -> bool:
    return any(item["name"] == column for item in inspect(connection).get_columns(table))


def _legacy_migration_done(connection, table: str, column: str) -> bool:
    if connection.dialect.name != "postgresql":
        return False
    marker = connection.execute(text("""
        SELECT col_description(
            CAST(:table AS regclass),
            (SELECT ordinal_position FROM information_schema.columns
             WHERE table_schema = current_schema() AND table_name = :table
               AND column_name = :column)
        )
    """), {"table": table, "column": column}).scalar()
    return marker == "normalizado_v1"


def _mark_legacy_migration(connection, table: str, column: str) -> None:
    if connection.dialect.name == "postgresql":
        connection.exec_driver_sql(
            f'COMMENT ON COLUMN "{table}"."{column}" IS \'normalizado_v1\''
        )


def _insert_permission(connection, code: str) -> None:
    if connection.execute(
        text("SELECT 1 FROM permiso WHERE codigo = :codigo"), {"codigo": code},
    ).first():
        return
    connection.execute(
        text("INSERT INTO permiso (codigo, nombre) VALUES (:codigo, :nombre)"),
        {"codigo": code, "nombre": PERMISSION_NAMES.get(code, code.replace("_", " ").title())},
    )


def _migrate_profile_permissions(connection) -> None:
    if not _has_column(connection, "perfil", "permisos"):
        return
    if _legacy_migration_done(connection, "perfil", "permisos"):
        return
    for row in connection.execute(
        text("SELECT id_perfil, permisos FROM perfil WHERE permisos <> ''"),
    ).mappings():
        for code in sorted({item.strip() for item in (row["permisos"] or "").split(",") if item.strip()}):
            _insert_permission(connection, code)
            if not connection.execute(text("""
                SELECT 1 FROM perfil_permiso
                WHERE id_perfil = :id_perfil AND cod_permiso = :codigo
            """), {"id_perfil": row["id_perfil"], "codigo": code}).first():
                connection.execute(text("""
                    INSERT INTO perfil_permiso (id_perfil, cod_permiso)
                    VALUES (:id_perfil, :codigo)
                """), {"id_perfil": row["id_perfil"], "codigo": code})
    _mark_legacy_migration(connection, "perfil", "permisos")


def _migrate_enrollment_access(connection) -> None:
    if not _has_column(connection, "periodo_academico", "matricula_accesos"):
        return
    if _legacy_migration_done(connection, "periodo_academico", "matricula_accesos"):
        return
    plans = connection.execute(text(
        "SELECT cod_fac, cod_esc, corr_pe FROM plan_estudio"
    )).mappings().all()
    rows = connection.execute(text("""
        SELECT cod_periodo, matricula_accesos
        FROM periodo_academico
        WHERE matricula_accesos <> ''
    """)).mappings()
    for row in rows:
        try:
            values = json.loads(row["matricula_accesos"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        for raw_key, phase in values.items():
            if phase not in {"CERRADA", "TERCIO", "TODOS"}:
                continue
            parts = str(raw_key).split(":")
            try:
                cycle = int(parts[-1])
                plan_number = int(parts[0]) if len(parts) == 2 else None
            except ValueError:
                continue
            if not 1 <= cycle <= 10:
                continue
            applicable_plans = [
                plan for plan in plans
                if plan_number is None or plan["corr_pe"] == plan_number
            ]
            for plan in applicable_plans:
                params = {
                    "period": row["cod_periodo"], "faculty": plan["cod_fac"],
                    "school": plan["cod_esc"], "plan": plan["corr_pe"],
                    "cycle": cycle, "phase": phase,
                }
                if connection.execute(text("""
                    SELECT 1 FROM periodo_matricula_acceso
                    WHERE cod_periodo = :period AND cod_fac = :faculty
                      AND cod_esc = :school AND corr_pe = :plan AND ciclo = :cycle
                """), params).first():
                    continue
                connection.execute(text("""
                    INSERT INTO periodo_matricula_acceso
                        (cod_periodo, cod_fac, cod_esc, corr_pe, ciclo, fase)
                    VALUES (:period, :faculty, :school, :plan, :cycle, :phase)
                """), params)
    _mark_legacy_migration(connection, "periodo_academico", "matricula_accesos")


def _migrate_pre_enrollments(connection) -> None:
    if not _has_column(connection, "estudiante", "prematricula"):
        return
    if _legacy_migration_done(connection, "estudiante", "prematricula"):
        return
    rows = connection.execute(text("""
        SELECT cod_estudiante, prematricula
        FROM estudiante
        WHERE prematricula <> ''
    """)).mappings()
    for row in rows:
        try:
            payload = json.loads(row["prematricula"] or "{}")
            period = str(payload.get("cod_periodo", ""))
            offer_ids = sorted({int(value) for value in payload.get("ofertas", [])})
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not period or not connection.execute(
            text("SELECT 1 FROM periodo_academico WHERE cod_periodo = :period"),
            {"period": period},
        ).first():
            continue
        pre_enrollment_id = connection.execute(text("""
            SELECT id_prematricula FROM prematricula
            WHERE cod_estudiante = :student
        """), {"student": row["cod_estudiante"]}).scalar()
        if pre_enrollment_id is None:
            connection.execute(text("""
                INSERT INTO prematricula (cod_estudiante, cod_periodo)
                VALUES (:student, :period)
            """), {"student": row["cod_estudiante"], "period": period})
            pre_enrollment_id = connection.execute(text("""
                SELECT id_prematricula FROM prematricula
                WHERE cod_estudiante = :student
            """), {"student": row["cod_estudiante"]}).scalar_one()
        for offer_id in offer_ids:
            if not connection.execute(text("""
                SELECT 1 FROM oferta_curso
                WHERE id_oferta = :offer AND cod_periodo = :period
            """), {"offer": offer_id, "period": period}).first():
                continue
            if not connection.execute(text("""
                SELECT 1 FROM prematricula_detalle
                WHERE id_prematricula = :pre_enrollment AND id_oferta = :offer
            """), {"pre_enrollment": pre_enrollment_id, "offer": offer_id}).first():
                connection.execute(text("""
                    INSERT INTO prematricula_detalle (id_prematricula, id_oferta)
                    VALUES (:pre_enrollment, :offer)
                """), {"pre_enrollment": pre_enrollment_id, "offer": offer_id})
    _mark_legacy_migration(connection, "estudiante", "prematricula")


def _ensure_teacher_foreign_key(connection) -> None:
    if connection.dialect.name != "postgresql":
        return
    connection.exec_driver_sql("""
        UPDATE oferta_curso AS oferta
        SET cod_docente = NULL
        WHERE cod_docente IS NOT NULL
          AND (
              LENGTH(cod_docente) > 12 OR NOT EXISTS (
                  SELECT 1 FROM docente AS docente
                  WHERE docente.cod_fac = oferta.cod_fac
                    AND docente.cod_esc = oferta.cod_esc
                    AND docente.cod_docente = oferta.cod_docente
              )
          )
    """)
    teacher_column = next(
        column for column in inspect(connection).get_columns("oferta_curso")
        if column["name"] == "cod_docente"
    )
    if getattr(teacher_column["type"], "length", None) != 12:
        connection.exec_driver_sql(
            "ALTER TABLE oferta_curso ALTER COLUMN cod_docente TYPE VARCHAR(12)"
        )
    connection.exec_driver_sql("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_oferta_docente'
            ) THEN
                ALTER TABLE oferta_curso
                ADD CONSTRAINT fk_oferta_docente
                FOREIGN KEY (cod_fac, cod_esc, cod_docente)
                REFERENCES docente(cod_fac, cod_esc, cod_docente);
            END IF;
        END $$
    """)


def run_migrations(engine: Engine) -> None:
    """Aplica migraciones incrementales e idempotentes sin eliminar datos."""
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql(
                "ALTER TABLE oferta_curso ADD COLUMN IF NOT EXISTS cod_docente VARCHAR(12)"
            )
            connection.exec_driver_sql(
                "ALTER TABLE matricula_detalle ADD COLUMN IF NOT EXISTS nota_practicas INTEGER"
            )
            connection.exec_driver_sql(
                "ALTER TABLE matricula_detalle ADD COLUMN IF NOT EXISTS nota_parcial INTEGER"
            )
            connection.exec_driver_sql(
                "ALTER TABLE matricula_detalle ADD COLUMN IF NOT EXISTS nota_examen_final INTEGER"
            )
        _ensure_teacher_foreign_key(connection)
        _migrate_profile_permissions(connection)
        _migrate_enrollment_access(connection)
        _migrate_pre_enrollments(connection)
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_oferta_docente ON oferta_curso(cod_fac, cod_esc, cod_docente)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_prematricula_detalle_oferta ON prematricula_detalle(id_oferta)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_perfil_permiso_codigo ON perfil_permiso(cod_permiso)"
        )
        connection.exec_driver_sql("""
            UPDATE matricula_detalle
            SET nota_practicas = COALESCE(nota_practicas, nota_final),
                nota_parcial = COALESCE(nota_parcial, nota_final),
                nota_examen_final = COALESCE(nota_examen_final, nota_final)
            WHERE nota_final IS NOT NULL
              AND (nota_practicas IS NULL OR nota_parcial IS NULL OR nota_examen_final IS NULL)
        """)
        connection.exec_driver_sql("""
            UPDATE plan_estudio
            SET den_plan = CASE
                WHEN anio_plan = 2010 THEN 'Plan Curricular 2010'
                WHEN anio_plan = 2019 THEN 'Plan de Estudios 2019'
                ELSE den_plan
            END
            WHERE anio_plan IN (2010, 2019)
        """)
