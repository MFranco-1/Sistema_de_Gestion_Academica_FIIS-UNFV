import unittest
from datetime import date
from types import SimpleNamespace

from sqlalchemy import create_engine, text
from sqlalchemy.orm import configure_mappers

from app import models
from app.crud import (
    _cumple_regla_avance,
    _curso_relevante_periodo,
    _motivo_bloqueo_oferta,
    _ventana_suspension_trica,
)
from app.migrations import (
    _migrate_enrollment_access,
    _migrate_pre_enrollments,
    _migrate_profile_permissions,
)


class AcademicRulesTest(unittest.TestCase):
    def test_regular_period_parity_and_summer(self):
        self.assertTrue(_curso_relevante_periodo("I", 3, False))
        self.assertFalse(_curso_relevante_periodo("I", 4, False))
        self.assertTrue(_curso_relevante_periodo("II", 4, False))
        self.assertFalse(_curso_relevante_periodo("II", 3, True))
        self.assertTrue(_curso_relevante_periodo("VERANO", 3, True))
        self.assertFalse(_curso_relevante_periodo("VERANO", 3, False))

    def test_prerequisites_and_capacity_block_enrollment(self):
        missing = _motivo_bloqueo_oferta(
            "ACTIVO", False, False, 3, 3, {"P19-16"}, 10, 35, True, True,
        )
        full = _motivo_bloqueo_oferta(
            "ACTIVO", False, False, 3, 3, set(), 35, 35, True, True,
        )
        available = _motivo_bloqueo_oferta(
            "ACTIVO", False, False, 3, 3, set(), 34, 35, True, True,
        )
        self.assertEqual(missing, "Falta aprobar: P19-16")
        self.assertEqual(full, "No quedan vacantes.")
        self.assertEqual(available, "")

    def test_cycle_advances_only_after_complete_sufficient_regular_load(self):
        self.assertFalse(_cumple_regla_avance("I", [("APROBADO", 4)]))
        self.assertFalse(_cumple_regla_avance(
            "I", [("APROBADO", 4), ("MATRICULADO", 4)],
        ))
        self.assertFalse(_cumple_regla_avance(
            "VERANO", [("APROBADO", 4), ("APROBADO", 4)],
        ))
        self.assertFalse(_cumple_regla_avance(
            "II", [("APROBADO", 3), ("APROBADO", 3), ("DESAPROBADO", 8)],
        ))
        self.assertTrue(_cumple_regla_avance(
            "II", [("APROBADO", 4), ("APROBADO", 4), ("DESAPROBADO", 4)],
        ))

    def test_third_failure_suspends_two_regular_periods_and_intermediate_summer(self):
        periods = [
            SimpleNamespace(cod_periodo="2025-II", tipo_periodo="II", fecha_inicio=date(2025, 8, 18)),
            SimpleNamespace(cod_periodo="2026-V", tipo_periodo="VERANO", fecha_inicio=date(2026, 1, 5)),
            SimpleNamespace(cod_periodo="2026-I", tipo_periodo="I", fecha_inicio=date(2026, 3, 16)),
            SimpleNamespace(cod_periodo="2026-II", tipo_periodo="II", fecha_inicio=date(2026, 8, 17)),
        ]
        suspended, return_period, active_regular = _ventana_suspension_trica(
            date(2025, 3, 17), periods, date(2025, 8, 18),
        )
        _, _, active_summer = _ventana_suspension_trica(
            date(2025, 3, 17), periods, date(2026, 1, 5),
        )
        _, _, active_return = _ventana_suspension_trica(
            date(2025, 3, 17), periods, date(2026, 8, 17),
        )
        self.assertEqual([item.cod_periodo for item in suspended], ["2025-II", "2026-I"])
        self.assertEqual(return_period.cod_periodo, "2026-II")
        self.assertTrue(active_regular)
        self.assertTrue(active_summer)
        self.assertFalse(active_return)


class NormalizedSchemaTest(unittest.TestCase):
    def test_normalized_tables_and_teacher_foreign_key_exist(self):
        configure_mappers()
        for table in (
            "prematricula", "prematricula_detalle", "periodo_matricula_acceso",
            "permiso", "perfil_permiso",
        ):
            self.assertIn(table, models.Base.metadata.tables)
        self.assertNotIn("prematricula", models.Estudiante.__table__.c)
        self.assertNotIn("matricula_accesos", models.PeriodoAcademico.__table__.c)
        self.assertNotIn("permisos", models.Perfil.__table__.c)
        teacher_fk = next(
            constraint for constraint in models.OfertaCurso.__table__.foreign_key_constraints
            if constraint.name == "fk_oferta_docente"
        )
        self.assertEqual(
            {element.target_fullname for element in teacher_fk.elements},
            {"docente.cod_fac", "docente.cod_esc", "docente.cod_docente"},
        )
        self.assertEqual(models.OfertaCurso.__table__.c.cod_docente.type.length, 12)

    def test_enrollment_keeps_one_record_per_student_and_period(self):
        constraints = {constraint.name for constraint in models.Matricula.__table__.constraints}
        self.assertIn("uq_matricula_estudiante_periodo", constraints)


class LegacyDataMigrationTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        with self.engine.begin() as connection:
            for statement in (
                "CREATE TABLE perfil (id_perfil INTEGER PRIMARY KEY, permisos VARCHAR(500))",
                "CREATE TABLE permiso (codigo VARCHAR(40) PRIMARY KEY, nombre VARCHAR(100))",
                "CREATE TABLE perfil_permiso (id_perfil INTEGER, cod_permiso VARCHAR(40), PRIMARY KEY(id_perfil,cod_permiso))",
                "CREATE TABLE plan_estudio (cod_fac INTEGER, cod_esc INTEGER, corr_pe INTEGER)",
                "CREATE TABLE periodo_academico (cod_periodo VARCHAR(10) PRIMARY KEY, matricula_accesos VARCHAR(500))",
                "CREATE TABLE periodo_matricula_acceso (cod_periodo VARCHAR(10), cod_fac INTEGER, cod_esc INTEGER, corr_pe INTEGER, ciclo INTEGER, fase VARCHAR(10), PRIMARY KEY(cod_periodo,cod_fac,cod_esc,corr_pe,ciclo))",
                "CREATE TABLE estudiante (cod_estudiante VARCHAR(10) PRIMARY KEY, prematricula VARCHAR(1000))",
                "CREATE TABLE oferta_curso (id_oferta INTEGER PRIMARY KEY, cod_periodo VARCHAR(10))",
                "CREATE TABLE prematricula (id_prematricula INTEGER PRIMARY KEY AUTOINCREMENT, cod_estudiante VARCHAR(10) UNIQUE, cod_periodo VARCHAR(10))",
                "CREATE TABLE prematricula_detalle (id_prematricula INTEGER, id_oferta INTEGER, PRIMARY KEY(id_prematricula,id_oferta))",
            ):
                connection.exec_driver_sql(statement)
            connection.execute(text(
                "INSERT INTO perfil VALUES (1, 'GESTION_MATRICULAS,PLANA_DOCENTE')"
            ))
            connection.execute(text("INSERT INTO plan_estudio VALUES (1,1,2)"))
            connection.execute(text(
                "INSERT INTO periodo_academico VALUES ('2027-I', '{\"2:3\":\"TERCIO\"}')"
            ))
            connection.execute(text(
                "INSERT INTO estudiante VALUES ('2024000001', '{\"cod_periodo\":\"2027-I\",\"ofertas\":[10]}')"
            ))
            connection.execute(text("INSERT INTO oferta_curso VALUES (10, '2027-I')"))

    def test_legacy_values_are_copied_to_normalized_tables(self):
        with self.engine.begin() as connection:
            _migrate_profile_permissions(connection)
            _migrate_enrollment_access(connection)
            _migrate_pre_enrollments(connection)
            _migrate_profile_permissions(connection)
            _migrate_enrollment_access(connection)
            _migrate_pre_enrollments(connection)
            permissions = connection.execute(text(
                "SELECT cod_permiso FROM perfil_permiso ORDER BY cod_permiso"
            )).scalars().all()
            access = connection.execute(text(
                "SELECT corr_pe, ciclo, fase FROM periodo_matricula_acceso"
            )).one()
            guide = connection.execute(text("""
                SELECT p.cod_estudiante, p.cod_periodo, d.id_oferta
                FROM prematricula p
                JOIN prematricula_detalle d ON d.id_prematricula = p.id_prematricula
            """)).one()
        self.assertEqual(permissions, ["GESTION_MATRICULAS", "PLANA_DOCENTE"])
        self.assertEqual(tuple(access), (2, 3, "TERCIO"))
        self.assertEqual(tuple(guide), ("2024000001", "2027-I", 10))


if __name__ == "__main__":
    unittest.main()
