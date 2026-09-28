"""Prueba destructiva para una base PostgreSQL temporal creada exclusivamente para CI/local."""

import os

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app import auth, crud, models, schemas
from app.database import SessionLocal, engine
from app.migrations import run_migrations


def main() -> None:
    if not os.getenv("ACADEMIC_TEST_DATABASE"):
        raise RuntimeError("Esta prueba solo puede ejecutarse contra una base temporal autorizada.")

    run_migrations(engine)
    run_migrations(engine)
    inspector = inspect(engine)
    expected_tables = {
        "prematricula", "prematricula_detalle", "periodo_matricula_acceso",
        "permiso", "perfil_permiso",
    }
    assert expected_tables.issubset(set(inspector.get_table_names()))
    teacher_column = next(
        column for column in inspector.get_columns("oferta_curso")
        if column["name"] == "cod_docente"
    )
    assert teacher_column["type"].length == 12
    assert any(fk["name"] == "fk_oferta_docente" for fk in inspector.get_foreign_keys("oferta_curso"))

    with SessionLocal() as db:
        period_types = {row[0] for row in db.query(models.PeriodoAcademico.tipo_periodo).distinct()}
        assert period_types == {"I", "II", "VERANO"}
        assert db.query(models.CursoPrerequisito).count() > 0
        assert db.query(models.Curso).count() > 0

        admin = db.query(models.Perfil).filter_by(codigo=auth.PERFIL_ADMIN).one()
        assert "GESTION_MATRICULAS" in auth.codigos_permisos(admin)
        authenticated, active_profile = crud.autenticar(db, "admin", "Admin123*")
        assert authenticated.id_usuario and active_profile == auth.PERFIL_ADMIN

        student = db.query(models.Estudiante).order_by(models.Estudiante.cod_estudiante).first()
        assert student is not None
        target_period = (
            db.query(models.PeriodoAcademico)
            .filter(models.PeriodoAcademico.tipo_periodo == ("I" if student.ciclo_actual % 2 else "II"))
            .order_by(models.PeriodoAcademico.fecha_inicio.desc())
            .first()
        )
        assert target_period is not None
        offers = crud.get_ofertas_estudiante(db, student.cod_estudiante, target_period.cod_periodo)
        assert all(offer["vacantes_disponibles"] >= 0 for offer in offers)

        guide_offer = (
            db.query(models.OfertaCurso)
            .filter_by(
                cod_periodo=target_period.cod_periodo, cod_fac=student.cod_fac,
                cod_esc=student.cod_esc, corr_pe=student.corr_pe,
            )
            .first()
        )
        assert guide_offer is not None
        crud.guardar_prematricula(
            db, student.cod_estudiante,
            schemas.Prematricula(cod_periodo=target_period.cod_periodo, ofertas=[guide_offer.id_oferta]),
        )
        saved_guide = crud.get_prematricula(db, student.cod_estudiante)
        assert saved_guide == {
            "cod_periodo": target_period.cod_periodo, "ofertas": [guide_offer.id_oferta],
        }

        crud.actualizar_acceso_matricula(
            db, target_period.cod_periodo, student.ciclo_actual,
            schemas.MatriculaAccesoUpdate(fase="TODOS"), student.corr_pe,
            student.cod_fac, student.cod_esc,
        )
        access = db.query(models.PeriodoMatriculaAcceso).filter_by(
            cod_periodo=target_period.cod_periodo, cod_fac=student.cod_fac,
            cod_esc=student.cod_esc, corr_pe=student.corr_pe,
            ciclo=student.ciclo_actual,
        ).one()
        assert access.fase == "TODOS"

        try:
            db.execute(text("""
                INSERT INTO oferta_curso
                    (cod_periodo, cod_fac, cod_esc, corr_pe, cod_curso,
                     cod_seccion, vacantes, activo, cod_docente)
                VALUES (:period, :faculty, :school, :plan, :course,
                        'FK-TEST', 1, TRUE, 'NO-EXISTE')
            """), {
                "period": guide_offer.cod_periodo, "faculty": guide_offer.cod_fac,
                "school": guide_offer.cod_esc, "plan": guide_offer.corr_pe,
                "course": guide_offer.cod_curso,
            })
            db.commit()
            raise AssertionError("La FK de docente aceptó un código inexistente.")
        except IntegrityError:
            db.rollback()

        vacancy = db.execute(text("""
            SELECT o.vacantes - COUNT(md.id_matricula) FILTER (
                       WHERE md.resultado <> 'RETIRADO'
                   ) AS disponibles
            FROM oferta_curso o
            LEFT JOIN matricula_detalle md ON md.id_oferta = o.id_oferta
            WHERE o.id_oferta = :offer
            GROUP BY o.id_oferta
        """), {"offer": guide_offer.id_oferta}).scalar_one()
        assert vacancy >= 0

    print("POSTGRES_INTEGRATION_OK")


if __name__ == "__main__":
    main()
