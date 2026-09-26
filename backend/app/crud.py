import json
from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, not_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth, models, schemas


def get_facultades(db: Session):
    return db.query(models.Facultad).order_by(models.Facultad.den_fac).all()


def get_escuelas(db: Session, cod_fac: int | None = None):
    query = db.query(models.Escuela)
    if cod_fac is not None:
        query = query.filter(models.Escuela.cod_fac == cod_fac)
    return query.order_by(models.Escuela.den_escuela).all()


def get_docentes(db: Session, buscar: str | None = None, categoria: str | None = None):
    query = db.query(models.Docente)
    if buscar:
        patron = f"%{buscar.strip()}%"
        query = query.filter(or_(
            models.Docente.cod_docente.ilike(patron),
            models.Docente.apellidos_nombres.ilike(patron),
        ))
    if categoria:
        query = query.filter(models.Docente.categoria == categoria)
    return query.order_by(models.Docente.apellidos_nombres).all()


def get_planes(db: Session, cod_fac: int | None = None, cod_esc: int | None = None):
    query = (
        db.query(
            models.PlanEstudio,
            func.count(models.Curso.cod_curso).label("total_cursos"),
            func.coalesce(func.sum(models.Curso.cred), 0).label("total_creditos"),
        )
        .outerjoin(
            models.Curso,
            (models.Curso.cod_fac == models.PlanEstudio.cod_fac)
            & (models.Curso.cod_esc == models.PlanEstudio.cod_esc)
            & (models.Curso.corr_pe == models.PlanEstudio.corr_pe),
        )
        .group_by(
            models.PlanEstudio.cod_fac,
            models.PlanEstudio.cod_esc,
            models.PlanEstudio.corr_pe,
        )
    )
    if cod_fac is not None:
        query = query.filter(models.PlanEstudio.cod_fac == cod_fac)
    if cod_esc is not None:
        query = query.filter(models.PlanEstudio.cod_esc == cod_esc)

    resultado = []
    for plan, total_cursos, total_creditos in query.order_by(models.PlanEstudio.anio_plan.desc()).all():
        resultado.append({
            "cod_fac": plan.cod_fac,
            "cod_esc": plan.cod_esc,
            "corr_pe": plan.corr_pe,
            "den_plan": plan.den_plan,
            "anio_plan": plan.anio_plan,
            "fecha_vigencia": plan.fecha_vigencia,
            "fecha_baja": plan.fecha_baja,
            "vigente": plan.vigente,
            "total_cursos": total_cursos,
            "total_creditos": total_creditos,
        })
    return resultado


def get_cursos(
    db: Session,
    cod_fac: int | None = None,
    cod_esc: int | None = None,
    corr_pe: int | None = None,
    semestre: int | None = None,
    buscar: str | None = None,
):
    query = db.query(models.Curso)
    if cod_fac is not None:
        query = query.filter(models.Curso.cod_fac == cod_fac)
    if cod_esc is not None:
        query = query.filter(models.Curso.cod_esc == cod_esc)
    if corr_pe is not None:
        query = query.filter(models.Curso.corr_pe == corr_pe)
    if semestre is not None:
        query = query.filter(models.Curso.semestre == semestre)
    if buscar:
        patron = f"%{buscar.strip()}%"
        query = query.filter(or_(models.Curso.cod_curso.ilike(patron), models.Curso.den_curso.ilike(patron)))

    cursos = query.order_by(models.Curso.semestre, models.Curso.cod_curso).all()
    if not cursos:
        return []

    claves_plan = {(c.cod_fac, c.cod_esc, c.corr_pe) for c in cursos}
    prerequisitos = db.query(models.CursoPrerequisito).filter(
        or_(*[
            (models.CursoPrerequisito.cod_fac == f)
            & (models.CursoPrerequisito.cod_esc == e)
            & (models.CursoPrerequisito.corr_pe == p)
            for f, e, p in claves_plan
        ])
    ).all()

    nombres = {
        (c.cod_fac, c.cod_esc, c.corr_pe, c.cod_curso): c.den_curso
        for c in db.query(models.Curso).filter(
            or_(*[
                (models.Curso.cod_fac == f) & (models.Curso.cod_esc == e) & (models.Curso.corr_pe == p)
                for f, e, p in claves_plan
            ])
        ).all()
    }
    mapa = {}
    for requisito in prerequisitos:
        clave = (requisito.cod_fac, requisito.cod_esc, requisito.corr_pe, requisito.cod_curso)
        nombre = nombres.get(
            (requisito.cod_fac, requisito.cod_esc, requisito.corr_pe, requisito.cod_curso_prerequisito),
            "",
        )
        mapa.setdefault(clave, []).append(f"{requisito.cod_curso_prerequisito} - {nombre}")

    return [
        {
            "cod_fac": c.cod_fac, "cod_esc": c.cod_esc, "corr_pe": c.corr_pe,
            "cod_curso": c.cod_curso, "den_curso": c.den_curso,
            "semestre": c.semestre, "ht": c.ht, "hp": c.hp, "cred": c.cred,
            "tipo_curso": c.tipo_curso,
            "prerrequisitos_nombres": ", ".join(mapa.get((c.cod_fac, c.cod_esc, c.corr_pe, c.cod_curso), [])) or "Ninguno",
        }
        for c in cursos
    ]


def get_periodos(db: Session):
    return db.query(models.PeriodoAcademico).order_by(models.PeriodoAcademico.cod_periodo.desc()).all()


def get_programacion(
    db: Session,
    corr_pe: int | None = None,
    cod_periodo: str | None = None,
    semestre: int | None = None,
):
    query = (
        db.query(
            models.HorarioCurso, models.HorarioCabecera, models.HorarioDetalle,
            models.Curso, models.PlanEstudio,
        )
        .join(models.HorarioCabecera, models.HorarioCabecera.id_horario == models.HorarioCurso.id_horario)
        .join(
            models.HorarioDetalle,
            (models.HorarioDetalle.id_horario == models.HorarioCurso.id_horario)
            & (models.HorarioDetalle.semestre_corr == models.HorarioCurso.semestre_corr),
        )
        .join(
            models.Curso,
            (models.Curso.cod_fac == models.HorarioCurso.cod_fac)
            & (models.Curso.cod_esc == models.HorarioCurso.cod_esc)
            & (models.Curso.corr_pe == models.HorarioCurso.corr_pe)
            & (models.Curso.cod_curso == models.HorarioCurso.cod_curso),
        )
        .join(
            models.PlanEstudio,
            (models.PlanEstudio.cod_fac == models.HorarioCabecera.cod_fac)
            & (models.PlanEstudio.cod_esc == models.HorarioCabecera.cod_esc)
            & (models.PlanEstudio.corr_pe == models.HorarioCabecera.corr_pe),
        )
    )
    if corr_pe is not None:
        query = query.filter(models.HorarioCabecera.corr_pe == corr_pe)
    if cod_periodo:
        query = query.filter(models.HorarioCabecera.cod_periodo == cod_periodo)
    if semestre is not None:
        query = query.filter(models.HorarioCurso.semestre_corr == semestre)

    orden_dias = case(
        {"LUNES": 1, "MARTES": 2, "MIERCOLES": 3, "JUEVES": 4, "VIERNES": 5, "SABADO": 6},
        value=models.HorarioCurso.dia_semana,
        else_=7,
    )
    query = query.order_by(orden_dias, models.HorarioCurso.hora_inicio)

    return [
        {
            "id_horario": h.id_horario, "cod_periodo": cab.cod_periodo,
            "corr_pe": cab.corr_pe, "den_plan": plan.den_plan,
            "semestre_corr": h.semestre_corr, "semestre_desc": det.semestre_desc,
            "cod_curso": h.cod_curso, "den_curso": curso.den_curso,
            "cod_seccion": h.cod_seccion, "tipo_sesion": h.tipo_sesion,
            "dia_semana": h.dia_semana, "hora_inicio": h.hora_inicio,
            "hora_fin": h.hora_fin, "aula": h.aula,
        }
        for h, cab, det, curso, plan in query.all()
    ]


def get_horarios_disponibles(
    db: Session,
    corr_pe: int | None = None,
    cod_periodo: str | None = None,
    semestre: int | None = None,
):
    query = (
        db.query(models.HorarioCabecera, models.HorarioDetalle)
        .join(models.HorarioDetalle, models.HorarioDetalle.id_horario == models.HorarioCabecera.id_horario)
    )
    if corr_pe is not None:
        query = query.filter(models.HorarioCabecera.corr_pe == corr_pe)
    if cod_periodo:
        query = query.filter(models.HorarioCabecera.cod_periodo == cod_periodo)
    if semestre is not None:
        query = query.filter(models.HorarioDetalle.semestre_corr == semestre)
    return [
        {
            "id_horario": cab.id_horario,
            "cod_periodo": cab.cod_periodo,
            "corr_pe": cab.corr_pe,
            "semestre_corr": det.semestre_corr,
            "semestre_desc": det.semestre_desc,
        }
        for cab, det in query.order_by(
            models.HorarioCabecera.cod_periodo.desc(), models.HorarioDetalle.semestre_corr,
        ).all()
    ]


def get_ofertas_administracion(
    db: Session, cod_periodo: str, corr_pe: int, semestre: int | None = None,
):
    query = db.query(models.OfertaCurso, models.Curso, models.Docente).join(
        models.Curso,
        (models.Curso.cod_fac == models.OfertaCurso.cod_fac)
        & (models.Curso.cod_esc == models.OfertaCurso.cod_esc)
        & (models.Curso.corr_pe == models.OfertaCurso.corr_pe)
        & (models.Curso.cod_curso == models.OfertaCurso.cod_curso),
    ).outerjoin(
        models.Docente,
        (models.Docente.cod_fac == models.OfertaCurso.cod_fac)
        & (models.Docente.cod_esc == models.OfertaCurso.cod_esc)
        & (models.Docente.cod_docente == models.OfertaCurso.cod_docente),
    ).filter(
        models.OfertaCurso.cod_periodo == cod_periodo,
        models.OfertaCurso.corr_pe == corr_pe,
    )
    if semestre is not None:
        query = query.filter(models.Curso.semestre == semestre)
    return [{
        "id_oferta": oferta.id_oferta, "cod_periodo": oferta.cod_periodo,
        "corr_pe": oferta.corr_pe, "cod_curso": oferta.cod_curso,
        "den_curso": curso.den_curso, "semestre": curso.semestre,
        "ht": curso.ht, "hp": curso.hp, "cod_seccion": oferta.cod_seccion,
        "vacantes": oferta.vacantes, "cod_docente": oferta.cod_docente,
        "docente_nombre": docente.apellidos_nombres if docente else "Sin asignar",
    } for oferta, curso, docente in query.order_by(
        models.Curso.semestre, models.Curso.cod_curso, models.OfertaCurso.cod_seccion,
    ).all()]


def asignar_docente_oferta(db: Session, id_oferta: int, datos: schemas.DocenteOfertaUpdate):
    oferta = db.query(models.OfertaCurso).filter_by(id_oferta=id_oferta).first()
    if not oferta:
        raise HTTPException(status_code=404, detail="La oferta académica no existe.")
    if datos.cod_docente:
        docente = db.query(models.Docente).filter_by(
            cod_fac=oferta.cod_fac, cod_esc=oferta.cod_esc, cod_docente=datos.cod_docente,
        ).first()
        if not docente:
            raise HTTPException(status_code=404, detail="El docente no pertenece a la escuela.")
    oferta.cod_docente = datos.cod_docente or None
    _commit(db, "No se pudo asignar el docente.")
    return {"mensaje": "Docente asignado correctamente."}


def get_semestres(db: Session, corr_pe: int, cod_fac: int = 1, cod_esc: int = 1):
    return [
        fila[0]
        for fila in (
            db.query(models.Curso.semestre)
            .filter(
                models.Curso.cod_fac == cod_fac,
                models.Curso.cod_esc == cod_esc,
                models.Curso.corr_pe == corr_pe,
            )
            .distinct()
            .order_by(models.Curso.semestre)
            .all()
        )
    ]


def get_curso_detalle(
    db: Session, corr_pe: int, cod_curso: str, cod_fac: int = 1, cod_esc: int = 1,
):
    curso = (
        db.query(models.Curso)
        .filter_by(cod_fac=cod_fac, cod_esc=cod_esc, corr_pe=corr_pe, cod_curso=cod_curso)
        .first()
    )
    if not curso:
        raise HTTPException(status_code=404, detail="El curso solicitado no existe en la malla indicada.")
    plan = (
        db.query(models.PlanEstudio)
        .filter_by(cod_fac=cod_fac, cod_esc=cod_esc, corr_pe=corr_pe)
        .one()
    )
    requisitos = (
        db.query(models.Curso)
        .join(
            models.CursoPrerequisito,
            and_(
                models.CursoPrerequisito.cod_fac == models.Curso.cod_fac,
                models.CursoPrerequisito.cod_esc == models.Curso.cod_esc,
                models.CursoPrerequisito.corr_pe == models.Curso.corr_pe,
                models.CursoPrerequisito.cod_curso_prerequisito == models.Curso.cod_curso,
            ),
        )
        .filter(
            models.CursoPrerequisito.cod_fac == cod_fac,
            models.CursoPrerequisito.cod_esc == cod_esc,
            models.CursoPrerequisito.corr_pe == corr_pe,
            models.CursoPrerequisito.cod_curso == cod_curso,
        )
        .order_by(models.Curso.semestre, models.Curso.cod_curso)
        .all()
    )
    dependientes = (
        db.query(models.Curso)
        .join(
            models.CursoPrerequisito,
            and_(
                models.CursoPrerequisito.cod_fac == models.Curso.cod_fac,
                models.CursoPrerequisito.cod_esc == models.Curso.cod_esc,
                models.CursoPrerequisito.corr_pe == models.Curso.corr_pe,
                models.CursoPrerequisito.cod_curso == models.Curso.cod_curso,
            ),
        )
        .filter(
            models.CursoPrerequisito.cod_fac == cod_fac,
            models.CursoPrerequisito.cod_esc == cod_esc,
            models.CursoPrerequisito.corr_pe == corr_pe,
            models.CursoPrerequisito.cod_curso_prerequisito == cod_curso,
        )
        .order_by(models.Curso.semestre, models.Curso.cod_curso)
        .all()
    )
    return {
        "cod_fac": curso.cod_fac,
        "cod_esc": curso.cod_esc,
        "corr_pe": curso.corr_pe,
        "cod_curso": curso.cod_curso,
        "den_curso": curso.den_curso,
        "semestre": curso.semestre,
        "ht": curso.ht,
        "hp": curso.hp,
        "cred": curso.cred,
        "tipo_curso": curso.tipo_curso,
        "prerrequisitos_nombres": ", ".join(f"{r.cod_curso} - {r.den_curso}" for r in requisitos) or "Ninguno",
        "den_plan": plan.den_plan,
        "anio_plan": plan.anio_plan,
        "prerrequisitos": [
            {"cod_curso": r.cod_curso, "den_curso": r.den_curso, "semestre": r.semestre}
            for r in requisitos
        ],
        "cursos_dependientes": [
            {"cod_curso": d.cod_curso, "den_curso": d.den_curso, "semestre": d.semestre}
            for d in dependientes
        ],
    }


def get_resumen_semestre(
    db: Session, corr_pe: int, semestre: int, cod_fac: int = 1, cod_esc: int = 1,
):
    con_requisito = (
        db.query(
            models.CursoPrerequisito.cod_fac,
            models.CursoPrerequisito.cod_esc,
            models.CursoPrerequisito.corr_pe,
            models.CursoPrerequisito.cod_curso,
        )
        .distinct()
        .subquery()
    )
    fila = (
        db.query(
            func.count(models.Curso.cod_curso),
            func.coalesce(func.sum(models.Curso.cred), 0),
            func.coalesce(func.sum(models.Curso.ht), 0),
            func.coalesce(func.sum(models.Curso.hp), 0),
            func.coalesce(func.sum(case((models.Curso.tipo_curso == "OBLIGATORIO", 1), else_=0)), 0),
            func.coalesce(func.sum(case((models.Curso.tipo_curso == "ELECTIVO", 1), else_=0)), 0),
            func.coalesce(func.sum(case((con_requisito.c.cod_curso.is_not(None), 1), else_=0)), 0),
            func.coalesce(func.sum(case((con_requisito.c.cod_curso.is_(None), 1), else_=0)), 0),
        )
        .outerjoin(
            con_requisito,
            and_(
                con_requisito.c.cod_fac == models.Curso.cod_fac,
                con_requisito.c.cod_esc == models.Curso.cod_esc,
                con_requisito.c.corr_pe == models.Curso.corr_pe,
                con_requisito.c.cod_curso == models.Curso.cod_curso,
            ),
        )
        .filter(
            models.Curso.cod_fac == cod_fac,
            models.Curso.cod_esc == cod_esc,
            models.Curso.corr_pe == corr_pe,
            models.Curso.semestre == semestre,
        )
        .one()
    )
    return {
        "corr_pe": corr_pe,
        "semestre": semestre,
        "total_cursos": fila[0],
        "total_creditos": fila[1],
        "horas_teoricas": fila[2],
        "horas_practicas": fila[3],
        "cursos_obligatorios": fila[4],
        "cursos_electivos": fila[5],
        "cursos_con_prerrequisitos": fila[6],
        "cursos_sin_prerrequisitos": fila[7],
    }


def _commit(db: Session, mensaje_conflicto: str):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=mensaje_conflicto) from exc


def crear_curso(db: Session, datos: schemas.CursoCreate):
    plan = db.query(models.PlanEstudio).filter_by(
        cod_fac=datos.cod_fac, cod_esc=datos.cod_esc, corr_pe=datos.corr_pe,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="La malla seleccionada no existe.")
    repetido = db.query(models.Curso).filter_by(
        cod_fac=datos.cod_fac, cod_esc=datos.cod_esc,
        corr_pe=datos.corr_pe, cod_curso=datos.cod_curso,
    ).first()
    if repetido:
        raise HTTPException(status_code=409, detail="El código del curso ya existe dentro de esta malla.")
    curso = models.Curso(**datos.model_dump())
    db.add(curso)
    _commit(db, "No se pudo registrar el curso porque sus datos entran en conflicto con la malla.")
    db.refresh(curso)
    return get_cursos(db, datos.cod_fac, datos.cod_esc, datos.corr_pe, buscar=datos.cod_curso)[0]


def editar_curso(
    db: Session, corr_pe: int, cod_curso: str, datos: schemas.CursoUpdate,
    cod_fac: int = 1, cod_esc: int = 1,
):
    curso = db.query(models.Curso).filter_by(
        cod_fac=cod_fac, cod_esc=cod_esc, corr_pe=corr_pe, cod_curso=cod_curso,
    ).first()
    if not curso:
        raise HTTPException(status_code=404, detail="El curso que desea editar no existe.")
    requisitos = (
        db.query(models.Curso)
        .join(models.CursoPrerequisito, and_(
            models.CursoPrerequisito.cod_fac == models.Curso.cod_fac,
            models.CursoPrerequisito.cod_esc == models.Curso.cod_esc,
            models.CursoPrerequisito.corr_pe == models.Curso.corr_pe,
            models.CursoPrerequisito.cod_curso_prerequisito == models.Curso.cod_curso,
        ))
        .filter_by(cod_fac=cod_fac, cod_esc=cod_esc, corr_pe=corr_pe)
        .filter(models.CursoPrerequisito.cod_curso == cod_curso)
        .all()
    )
    if any(req.semestre >= datos.semestre for req in requisitos):
        raise HTTPException(status_code=409, detail="El semestre debe ser posterior al de todos sus prerrequisitos.")
    dependientes = (
        db.query(models.Curso)
        .join(models.CursoPrerequisito, and_(
            models.CursoPrerequisito.cod_fac == models.Curso.cod_fac,
            models.CursoPrerequisito.cod_esc == models.Curso.cod_esc,
            models.CursoPrerequisito.corr_pe == models.Curso.corr_pe,
            models.CursoPrerequisito.cod_curso == models.Curso.cod_curso,
        ))
        .filter(models.CursoPrerequisito.cod_fac == cod_fac,
                models.CursoPrerequisito.cod_esc == cod_esc,
                models.CursoPrerequisito.corr_pe == corr_pe,
                models.CursoPrerequisito.cod_curso_prerequisito == cod_curso)
        .all()
    )
    if any(dep.semestre <= datos.semestre for dep in dependientes):
        raise HTTPException(status_code=409, detail="El semestre debe ser anterior al de todos los cursos dependientes.")
    for campo, valor in datos.model_dump().items():
        setattr(curso, campo, valor)
    _commit(db, "No se pudo actualizar el curso debido a una restricción académica.")
    return get_cursos(db, cod_fac, cod_esc, corr_pe, buscar=cod_curso)[0]


def eliminar_curso(
    db: Session, corr_pe: int, cod_curso: str, cod_fac: int = 1, cod_esc: int = 1,
):
    curso = db.query(models.Curso).filter_by(
        cod_fac=cod_fac, cod_esc=cod_esc, corr_pe=corr_pe, cod_curso=cod_curso,
    ).first()
    if not curso:
        raise HTTPException(status_code=404, detail="El curso que desea eliminar no existe.")
    dependientes = db.query(models.CursoPrerequisito).filter_by(
        cod_fac=cod_fac, cod_esc=cod_esc, corr_pe=corr_pe,
        cod_curso_prerequisito=cod_curso,
    ).count()
    if dependientes:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: el curso es prerrequisito de uno o más cursos.",
        )
    sesiones = db.query(models.HorarioCurso).filter_by(
        cod_fac=cod_fac, cod_esc=cod_esc, corr_pe=corr_pe, cod_curso=cod_curso,
    ).count()
    if sesiones:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: el curso tiene sesiones de horario registradas.",
        )
    db.delete(curso)
    _commit(db, "No se pudo eliminar el curso debido a registros académicos relacionados.")
    return {"mensaje": f"Curso {cod_curso} eliminado correctamente."}


def agregar_prerequisito(db: Session, datos: schemas.PrerequisitoCreate):
    if datos.cod_curso == datos.cod_curso_prerequisito:
        raise HTTPException(status_code=422, detail="Un curso no puede ser prerrequisito de sí mismo.")
    curso = db.query(models.Curso).filter_by(
        cod_fac=datos.cod_fac, cod_esc=datos.cod_esc, corr_pe=datos.corr_pe,
        cod_curso=datos.cod_curso,
    ).first()
    requisito = db.query(models.Curso).filter_by(
        cod_fac=datos.cod_fac, cod_esc=datos.cod_esc, corr_pe=datos.corr_pe,
        cod_curso=datos.cod_curso_prerequisito,
    ).first()
    if not curso or not requisito:
        raise HTTPException(status_code=404, detail="El curso y el prerrequisito deben existir en la misma malla.")
    if requisito.semestre >= curso.semestre:
        raise HTTPException(status_code=422, detail="El prerrequisito debe pertenecer a un semestre anterior.")
    existente = db.query(models.CursoPrerequisito).filter_by(**datos.model_dump()).first()
    if existente:
        raise HTTPException(status_code=409, detail="El prerrequisito ya está registrado para este curso.")
    db.add(models.CursoPrerequisito(**datos.model_dump()))
    _commit(db, "No se pudo agregar el prerrequisito.")
    return {"mensaje": "Prerrequisito agregado correctamente."}


def retirar_prerequisito(
    db: Session, corr_pe: int, cod_curso: str, cod_requisito: str,
    cod_fac: int = 1, cod_esc: int = 1,
):
    relacion = db.query(models.CursoPrerequisito).filter_by(
        cod_fac=cod_fac, cod_esc=cod_esc, corr_pe=corr_pe,
        cod_curso=cod_curso, cod_curso_prerequisito=cod_requisito,
    ).first()
    if not relacion:
        raise HTTPException(status_code=404, detail="La relación de prerrequisito no existe.")
    db.delete(relacion)
    _commit(db, "No se pudo retirar el prerrequisito.")
    return {"mensaje": "Prerrequisito retirado correctamente."}


def _buscar_sesion(db: Session, locator: schemas.SesionLocator):
    return db.query(models.HorarioCurso).filter_by(**locator.model_dump()).first()


def _minutos(valor) -> int:
    return valor.hour * 60 + valor.minute


def _turno_semestre(semestre: int, seccion: str) -> tuple[str, int, int]:
    seccion = seccion.upper()
    if semestre <= 2 or (semestre == 3 and seccion != "C"):
        return "mañana", 8 * 60, 15 * 60
    if semestre <= 5 or (semestre == 6 and seccion == "A") or semestre == 3:
        return "tarde", 13 * 60, 18 * 60
    # Seis bloques académicos de 50 min: el último termina a las 22:10.
    return "noche", 17 * 60 + 10, 22 * 60 + 10


def _validar_sesion(
    db: Session, datos: schemas.SesionCreate, excluir: schemas.SesionLocator | None = None,
):
    if datos.hora_fin <= datos.hora_inicio:
        raise HTTPException(status_code=422, detail="La hora final debe ser mayor que la hora inicial.")
    cabecera = db.query(models.HorarioCabecera).filter_by(id_horario=datos.id_horario).first()
    if not cabecera:
        raise HTTPException(status_code=404, detail="La cabecera de horario indicada no existe.")
    if (cabecera.cod_fac, cabecera.cod_esc, cabecera.corr_pe) != (
        datos.cod_fac, datos.cod_esc, datos.corr_pe,
    ):
        raise HTTPException(status_code=422, detail="La sesión no pertenece a la malla del horario.")
    detalle = db.query(models.HorarioDetalle).filter_by(
        id_horario=datos.id_horario, semestre_corr=datos.semestre_corr,
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="El semestre no está habilitado en este horario.")
    curso = db.query(models.Curso).filter_by(
        cod_fac=datos.cod_fac, cod_esc=datos.cod_esc, corr_pe=datos.corr_pe,
        cod_curso=datos.cod_curso,
    ).first()
    if not curso:
        raise HTTPException(status_code=404, detail="El curso no existe en la malla del horario.")
    if curso.semestre != datos.semestre_corr:
        raise HTTPException(status_code=422, detail="El curso no pertenece al semestre del horario.")
    duracion = _minutos(datos.hora_fin) - _minutos(datos.hora_inicio)
    if duracion <= 0 or duracion % 50 != 0:
        raise HTTPException(status_code=422, detail="Cada sesión debe usar bloques completos de 50 minutos académicos.")
    turno, inicio_turno, fin_turno = _turno_semestre(datos.semestre_corr, datos.cod_seccion)
    if _minutos(datos.hora_inicio) < inicio_turno or _minutos(datos.hora_fin) > fin_turno:
        raise HTTPException(
            status_code=422,
            detail=f"La sección {datos.cod_seccion} del ciclo {datos.semestre_corr} pertenece al turno {turno}.",
        )
    horas_requeridas = curso.ht if datos.tipo_sesion == "T" else curso.hp
    if horas_requeridas <= 0:
        raise HTTPException(status_code=422, detail="La malla no asigna horas para este tipo de sesión.")
    sesiones_tipo = db.query(models.HorarioCurso).filter_by(
        id_horario=datos.id_horario, semestre_corr=datos.semestre_corr,
        cod_curso=datos.cod_curso, cod_seccion=datos.cod_seccion,
        tipo_sesion=datos.tipo_sesion,
    ).all()
    minutos_asignados = sum(_minutos(item.hora_fin) - _minutos(item.hora_inicio) for item in sesiones_tipo)
    if excluir:
        original = _buscar_sesion(db, excluir)
        if original:
            minutos_asignados -= _minutos(original.hora_fin) - _minutos(original.hora_inicio)
    if minutos_asignados + duracion > horas_requeridas * 50:
        disponibles = max((horas_requeridas * 50 - minutos_asignados) // 50, 0)
        raise HTTPException(
            status_code=422,
            detail=f"La malla exige {horas_requeridas} hora(s) académica(s) de tipo {datos.tipo_sesion}; quedan {disponibles} por asignar.",
        )

    solape = and_(
        models.HorarioCurso.dia_semana == datos.dia_semana,
        models.HorarioCurso.hora_inicio < datos.hora_fin,
        models.HorarioCurso.hora_fin > datos.hora_inicio,
    )
    excluir_filtro = None
    if excluir:
        excluir_filtro = not_(and_(
            models.HorarioCurso.id_horario == excluir.id_horario,
            models.HorarioCurso.semestre_corr == excluir.semestre_corr,
            models.HorarioCurso.cod_curso == excluir.cod_curso,
            models.HorarioCurso.cod_seccion == excluir.cod_seccion,
            models.HorarioCurso.tipo_sesion == excluir.tipo_sesion,
            models.HorarioCurso.dia_semana == excluir.dia_semana,
            models.HorarioCurso.hora_inicio == excluir.hora_inicio,
        ))
    aula_query = (
        db.query(models.HorarioCurso)
        .join(models.HorarioCabecera, models.HorarioCabecera.id_horario == models.HorarioCurso.id_horario)
        .filter(models.HorarioCabecera.cod_periodo == cabecera.cod_periodo, solape,
                models.HorarioCurso.aula == datos.aula)
    )
    seccion_query = db.query(models.HorarioCurso).filter(
        models.HorarioCurso.id_horario == datos.id_horario,
        models.HorarioCurso.semestre_corr == datos.semestre_corr,
        models.HorarioCurso.cod_seccion == datos.cod_seccion,
        solape,
    )
    if excluir_filtro is not None:
        aula_query = aula_query.filter(excluir_filtro)
        seccion_query = seccion_query.filter(excluir_filtro)
    if aula_query.first():
        raise HTTPException(status_code=409, detail="El aula ya está ocupada en ese día y rango horario.")
    if seccion_query.first():
        raise HTTPException(status_code=409, detail="La sección ya tiene otra sesión en ese rango horario.")


def crear_sesion(db: Session, datos: schemas.SesionCreate):
    _validar_sesion(db, datos)
    db.add(models.HorarioCurso(**datos.model_dump()))
    _commit(db, "La sesión ya existe o entra en conflicto con el horario.")
    return {"mensaje": "Sesión de horario registrada correctamente."}


def editar_sesion(db: Session, datos: schemas.SesionEdicion):
    sesion = _buscar_sesion(db, datos.original)
    if not sesion:
        raise HTTPException(status_code=404, detail="La sesión que desea editar no existe.")
    _validar_sesion(db, datos.sesion, datos.original)
    for campo, valor in datos.sesion.model_dump().items():
        setattr(sesion, campo, valor)
    _commit(db, "No se pudo actualizar la sesión porque sus datos ya existen o se cruzan.")
    return {"mensaje": "Sesión de horario actualizada correctamente."}


def guardar_programacion_curso(db: Session, datos: schemas.ProgramacionCursoUpsert):
    cabecera = db.query(models.HorarioCabecera).filter_by(id_horario=datos.id_horario).first()
    if not cabecera or cabecera.corr_pe != datos.corr_pe:
        raise HTTPException(status_code=404, detail="El horario no pertenece a la malla seleccionada.")
    curso = db.query(models.Curso).filter_by(
        cod_fac=1, cod_esc=1, corr_pe=datos.corr_pe, cod_curso=datos.cod_curso,
    ).first()
    if not curso or curso.semestre != datos.semestre_corr:
        raise HTTPException(status_code=404, detail="El curso no pertenece al ciclo seleccionado.")
    if curso.ht and not datos.teoria:
        raise HTTPException(status_code=422, detail=f"La malla exige {curso.ht} hora(s) teóricas.")
    if curso.hp and not datos.practica:
        raise HTTPException(status_code=422, detail=f"La malla exige {curso.hp} hora(s) prácticas.")
    if not db.query(models.OfertaCurso).filter_by(
        cod_fac=cabecera.cod_fac, cod_esc=cabecera.cod_esc, corr_pe=datos.corr_pe,
        cod_curso=datos.cod_curso, cod_seccion=datos.cod_seccion,
        cod_periodo=cabecera.cod_periodo,
    ).first():
        raise HTTPException(status_code=404, detail="Primero debe abrir la sección para este curso.")
    existentes = db.query(models.HorarioCurso).filter_by(
        id_horario=datos.id_horario, semestre_corr=datos.semestre_corr,
        cod_curso=datos.cod_curso, cod_seccion=datos.cod_seccion,
    ).all()
    try:
        for item in existentes:
            db.delete(item)
        db.flush()
        for tipo, horas, bloque in (("T", curso.ht, datos.teoria), ("P", curso.hp, datos.practica)):
            if not horas:
                continue
            fin = (datetime.combine(date.today(), bloque.hora_inicio) + timedelta(minutes=horas * 50)).time()
            sesion = schemas.SesionCreate(
                id_horario=datos.id_horario, semestre_corr=datos.semestre_corr,
                cod_curso=datos.cod_curso, cod_seccion=datos.cod_seccion,
                tipo_sesion=tipo, corr_pe=datos.corr_pe,
                dia_semana=bloque.dia_semana, hora_inicio=bloque.hora_inicio,
                hora_fin=fin, aula=datos.aula,
            )
            _validar_sesion(db, sesion)
            db.add(models.HorarioCurso(**sesion.model_dump()))
            db.flush()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="La programación se cruza con otra clase o aula.")
    return {"mensaje": "Horario teórico y práctico guardado para la misma sección y aula."}


def get_estudiantes(db: Session, buscar: str | None = None):
    query = db.query(models.Estudiante, models.PlanEstudio).join(
        models.PlanEstudio,
        and_(
            models.PlanEstudio.cod_fac == models.Estudiante.cod_fac,
            models.PlanEstudio.cod_esc == models.Estudiante.cod_esc,
            models.PlanEstudio.corr_pe == models.Estudiante.corr_pe,
        ),
    )
    if buscar:
        patron = f"%{buscar.strip()}%"
        query = query.filter(or_(
            models.Estudiante.cod_estudiante.ilike(patron),
            models.Estudiante.dni.ilike(patron),
            models.Estudiante.apellidos_nombres.ilike(patron),
        ))
    resultado = []
    for e, p in query.order_by(models.Estudiante.apellidos_nombres).all():
        creditos_aprobados = db.query(func.coalesce(func.sum(models.Curso.cred), 0)).select_from(
            models.MatriculaDetalle
        ).join(models.Matricula, models.Matricula.id_matricula == models.MatriculaDetalle.id_matricula).join(
            models.OfertaCurso, models.OfertaCurso.id_oferta == models.MatriculaDetalle.id_oferta
        ).join(models.Curso, and_(
            models.Curso.cod_fac == models.OfertaCurso.cod_fac,
            models.Curso.cod_esc == models.OfertaCurso.cod_esc,
            models.Curso.corr_pe == models.OfertaCurso.corr_pe,
            models.Curso.cod_curso == models.OfertaCurso.cod_curso,
        )).filter(
            models.Matricula.cod_estudiante == e.cod_estudiante,
            models.MatriculaDetalle.resultado == "APROBADO",
        ).scalar() or 0
        creditos_matriculados = db.query(func.coalesce(func.sum(models.Curso.cred), 0)).select_from(
            models.MatriculaDetalle
        ).join(models.Matricula, models.Matricula.id_matricula == models.MatriculaDetalle.id_matricula).join(
            models.OfertaCurso, models.OfertaCurso.id_oferta == models.MatriculaDetalle.id_oferta
        ).join(models.Curso, and_(
            models.Curso.cod_fac == models.OfertaCurso.cod_fac,
            models.Curso.cod_esc == models.OfertaCurso.cod_esc,
            models.Curso.corr_pe == models.OfertaCurso.corr_pe,
            models.Curso.cod_curso == models.OfertaCurso.cod_curso,
        )).filter(
            models.Matricula.cod_estudiante == e.cod_estudiante,
            models.MatriculaDetalle.resultado == "MATRICULADO",
        ).scalar() or 0
        resultado.append({
            "cod_estudiante": e.cod_estudiante, "dni": e.dni,
            "apellidos_nombres": e.apellidos_nombres, "correo": e.correo,
            "cod_fac": e.cod_fac, "cod_esc": e.cod_esc, "corr_pe": e.corr_pe,
            "ciclo_actual": e.ciclo_actual, "estado": e.estado, "den_plan": p.den_plan,
            "anio_ingreso": int(e.correo[:4]) if e.correo[:4].isdigit() else int(e.cod_estudiante[:4]),
            "creditos_aprobados": int(creditos_aprobados),
            "creditos_matriculados": int(creditos_matriculados),
        })
    return resultado


def crear_estudiante(db: Session, datos: schemas.EstudianteCreate):
    if datos.correo[:4] != datos.cod_estudiante[:4]:
        raise HTTPException(
            status_code=422,
            detail="Los primeros cuatro dígitos del correo deben coincidir con el año de ingreso indicado en el código.",
        )
    plan = db.query(models.PlanEstudio).filter_by(
        cod_fac=datos.cod_fac, cod_esc=datos.cod_esc, corr_pe=datos.corr_pe,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="La malla seleccionada no existe.")
    estudiante = models.Estudiante(**datos.model_dump())
    db.add(estudiante)
    try:
        db.flush()
        auth.ensure_student_user(db, estudiante)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="El código, DNI, correo o usuario ya se encuentra registrado.",
        ) from exc
    _commit(db, "El código, DNI o correo ya pertenece a otro estudiante.")
    return get_estudiantes(db, datos.cod_estudiante)[0]


def editar_estudiante(db: Session, codigo: str, datos: schemas.EstudianteUpdate):
    estudiante = db.query(models.Estudiante).filter_by(cod_estudiante=codigo).first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="El estudiante no existe.")
    if datos.correo[:4] != codigo[:4]:
        raise HTTPException(
            status_code=422,
            detail="Los primeros cuatro dígitos del correo deben coincidir con el año de ingreso del estudiante.",
        )
    plan = db.query(models.PlanEstudio).filter_by(
        cod_fac=datos.cod_fac, cod_esc=datos.cod_esc, corr_pe=datos.corr_pe,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="La malla seleccionada no existe.")
    tiene_matriculas = db.query(models.Matricula).filter_by(cod_estudiante=codigo).first()
    if tiene_matriculas and estudiante.corr_pe != datos.corr_pe:
        raise HTTPException(
            status_code=409,
            detail="No se puede cambiar la malla porque el estudiante ya tiene historial académico.",
        )
    for campo, valor in datos.model_dump().items():
        setattr(estudiante, campo, valor)
    usuario = db.query(models.Usuario).filter_by(cod_estudiante=codigo).first()
    if usuario:
        usuario.nombre_mostrar = datos.apellidos_nombres
        usuario.clave_hash = auth.hash_password(datos.dni)
    _commit(db, "El DNI o correo ya pertenece a otro estudiante.")
    return get_estudiantes(db, codigo)[0]


def eliminar_estudiante(db: Session, codigo: str):
    estudiante = db.query(models.Estudiante).filter_by(cod_estudiante=codigo).first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="El estudiante no existe.")
    if db.query(models.Matricula).filter_by(cod_estudiante=codigo).first():
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar al estudiante porque tiene matrículas registradas.",
        )
    usuario = db.query(models.Usuario).filter_by(cod_estudiante=codigo).first()
    if usuario:
        perfil_estudiante = next(
            (perfil for perfil in usuario.perfiles if perfil.codigo == auth.PERFIL_ESTUDIANTE), None,
        )
        if len(usuario.perfiles) == 1 and perfil_estudiante:
            db.delete(usuario)
        else:
            if perfil_estudiante:
                usuario.perfiles.remove(perfil_estudiante)
            usuario.cod_estudiante = None
    db.delete(estudiante)
    _commit(db, "No se pudo eliminar al estudiante.")
    return {"mensaje": f"Estudiante {codigo} eliminado correctamente."}


def _aprobados_estudiante(db: Session, codigo: str) -> set[str]:
    return {
        fila[0]
        for fila in (
            db.query(models.OfertaCurso.cod_curso)
            .join(models.MatriculaDetalle, models.MatriculaDetalle.id_oferta == models.OfertaCurso.id_oferta)
            .join(models.Matricula, models.Matricula.id_matricula == models.MatriculaDetalle.id_matricula)
            .filter(
                models.Matricula.cod_estudiante == codigo,
                models.MatriculaDetalle.resultado == "APROBADO",
            )
            .distinct()
            .all()
        )
    }


def get_ofertas_estudiante(db: Session, codigo: str, cod_periodo: str):
    estudiante = db.query(models.Estudiante).filter_by(cod_estudiante=codigo).first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="El estudiante no existe.")
    periodo = db.query(models.PeriodoAcademico).filter_by(cod_periodo=cod_periodo).first()
    if not periodo:
        raise HTTPException(status_code=404, detail="El período académico no existe.")

    aprobados = _aprobados_estudiante(db, codigo)
    desaprobados = {
        fila[0] for fila in db.query(models.OfertaCurso.cod_curso)
        .join(models.MatriculaDetalle, models.MatriculaDetalle.id_oferta == models.OfertaCurso.id_oferta)
        .join(models.Matricula, models.Matricula.id_matricula == models.MatriculaDetalle.id_matricula)
        .filter(models.Matricula.cod_estudiante == codigo,
                models.MatriculaDetalle.resultado == "DESAPROBADO").distinct().all()
    }
    matricula_periodo = db.query(models.Matricula).filter_by(
        cod_estudiante=codigo, cod_periodo=cod_periodo,
    ).first()
    requisitos = db.query(models.CursoPrerequisito).filter_by(
        cod_fac=estudiante.cod_fac, cod_esc=estudiante.cod_esc, corr_pe=estudiante.corr_pe,
    ).all()
    requisitos_por_curso: dict[str, set[str]] = {}
    for requisito in requisitos:
        requisitos_por_curso.setdefault(requisito.cod_curso, set()).add(
            requisito.cod_curso_prerequisito,
        )

    filas = (
        db.query(
            models.OfertaCurso, models.Curso,
            func.count(models.MatriculaDetalle.id_matricula).label("matriculados"),
        )
        .join(models.Curso, and_(
            models.Curso.cod_fac == models.OfertaCurso.cod_fac,
            models.Curso.cod_esc == models.OfertaCurso.cod_esc,
            models.Curso.corr_pe == models.OfertaCurso.corr_pe,
            models.Curso.cod_curso == models.OfertaCurso.cod_curso,
        ))
        .outerjoin(
            models.MatriculaDetalle,
            and_(
                models.MatriculaDetalle.id_oferta == models.OfertaCurso.id_oferta,
                models.MatriculaDetalle.resultado != "RETIRADO",
            ),
        )
        .filter(
            models.OfertaCurso.cod_periodo == cod_periodo,
            models.OfertaCurso.cod_fac == estudiante.cod_fac,
            models.OfertaCurso.cod_esc == estudiante.cod_esc,
            models.OfertaCurso.corr_pe == estudiante.corr_pe,
            models.OfertaCurso.activo.is_(True),
            or_(models.Curso.semestre == estudiante.ciclo_actual,
                models.Curso.cod_curso.in_(desaprobados)),
        )
        .group_by(models.OfertaCurso.id_oferta, models.Curso.cod_fac,
                  models.Curso.cod_esc, models.Curso.corr_pe, models.Curso.cod_curso)
        .order_by(models.Curso.semestre, models.Curso.cod_curso)
        .all()
    )

    resultado = []
    for oferta, curso, matriculados in filas:
        docente = db.query(models.Docente).filter_by(
            cod_fac=oferta.cod_fac, cod_esc=oferta.cod_esc, cod_docente=oferta.cod_docente,
        ).first() if oferta.cod_docente else None
        sesiones = (
            db.query(models.HorarioCurso)
            .join(models.HorarioCabecera, models.HorarioCabecera.id_horario == models.HorarioCurso.id_horario)
            .filter(
                models.HorarioCabecera.cod_periodo == cod_periodo,
                models.HorarioCabecera.corr_pe == oferta.corr_pe,
                models.HorarioCurso.cod_curso == oferta.cod_curso,
                models.HorarioCurso.cod_seccion == oferta.cod_seccion,
            )
            .order_by(models.HorarioCurso.dia_semana, models.HorarioCurso.hora_inicio)
            .all()
        )
        horario_resumen = " · ".join(
            f"{s.dia_semana.title()} {s.hora_inicio.strftime('%H:%M')}-{s.hora_fin.strftime('%H:%M')} ({s.tipo_sesion})"
            for s in sesiones
        ) or "Horario pendiente"
        minutos_teoria = sum(_minutos(s.hora_fin) - _minutos(s.hora_inicio) for s in sesiones if s.tipo_sesion == "T")
        minutos_practica = sum(_minutos(s.hora_fin) - _minutos(s.hora_inicio) for s in sesiones if s.tipo_sesion == "P")
        es_pendiente = curso.cod_curso in desaprobados
        if periodo.tipo_periodo == "VERANO":
            relevante_periodo = es_pendiente
        elif periodo.tipo_periodo == "I":
            relevante_periodo = curso.semestre % 2 == 1
        else:
            relevante_periodo = curso.semestre % 2 == 0
        if not relevante_periodo:
            continue
        faltantes = requisitos_por_curso.get(curso.cod_curso, set()) - aprobados
        motivo = ""
        if estudiante.estado != "ACTIVO":
            motivo = "El estudiante no se encuentra activo."
        elif matricula_periodo:
            motivo = "El estudiante ya registró su matrícula en este período."
        elif curso.cod_curso in aprobados:
            motivo = "Curso aprobado anteriormente."
        elif curso.semestre > estudiante.ciclo_actual:
            motivo = "Pertenece a un ciclo posterior."
        elif faltantes:
            motivo = "Falta aprobar: " + ", ".join(sorted(faltantes))
        elif matriculados >= oferta.vacantes:
            motivo = "No quedan vacantes."
        elif minutos_teoria != curso.ht * 50 or minutos_practica != curso.hp * 50:
            motivo = f"Horario incompleto: la malla exige {curso.ht} h teóricas y {curso.hp} h prácticas."
        elif len({s.aula for s in sesiones}) > 1:
            motivo = "La teoría y la práctica deben dictarse en la misma aula."
        resultado.append({
            "id_oferta": oferta.id_oferta, "cod_periodo": oferta.cod_periodo,
            "corr_pe": oferta.corr_pe, "cod_curso": oferta.cod_curso,
            "den_curso": curso.den_curso, "semestre": curso.semestre,
            "cred": curso.cred,
            "cod_seccion": oferta.cod_seccion, "vacantes": oferta.vacantes,
            "matriculados": matriculados,
            "vacantes_disponibles": max(oferta.vacantes - matriculados, 0),
            "disponible": not motivo, "motivo": motivo,
            "horario_resumen": horario_resumen,
            "horarios": [{
                "dia_semana": s.dia_semana, "hora_inicio": s.hora_inicio,
                "hora_fin": s.hora_fin, "tipo_sesion": s.tipo_sesion, "aula": s.aula,
            } for s in sesiones],
            "cod_docente": oferta.cod_docente,
            "docente_nombre": docente.apellidos_nombres if docente else "Por asignar",
        })
    return resultado


def abrir_seccion(db: Session, datos: schemas.OfertaSeccionCreate):
    if not db.query(models.PeriodoAcademico).filter_by(cod_periodo=datos.cod_periodo).first():
        raise HTTPException(status_code=404, detail="El período académico no existe.")
    if not db.query(models.Curso).filter_by(
        cod_fac=datos.cod_fac, cod_esc=datos.cod_esc, corr_pe=datos.corr_pe,
        cod_curso=datos.cod_curso,
    ).first():
        raise HTTPException(status_code=404, detail="El curso no pertenece a la malla seleccionada.")
    if db.query(models.OfertaCurso).filter_by(**datos.model_dump(exclude={"vacantes"})).first():
        raise HTTPException(status_code=409, detail="La sección ya está abierta para este curso y período.")
    db.add(models.OfertaCurso(**datos.model_dump(), activo=True))
    _commit(db, "No se pudo abrir la sección.")
    return {"mensaje": f"Sección {datos.cod_seccion} abierta con capacidad para {datos.vacantes} estudiantes."}


def crear_matricula(db: Session, datos: schemas.MatriculaCreate):
    estudiante = db.query(models.Estudiante).filter_by(
        cod_estudiante=datos.cod_estudiante,
    ).first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="El estudiante no existe.")
    if db.query(models.Matricula).filter_by(
        cod_estudiante=datos.cod_estudiante, cod_periodo=datos.cod_periodo,
    ).first():
        raise HTTPException(status_code=409, detail="El estudiante ya tiene una matrícula en este período.")
    if len(datos.ofertas) != len(set(datos.ofertas)):
        raise HTTPException(status_code=422, detail="No se puede seleccionar dos veces la misma oferta.")

    disponibles = {
        oferta["id_oferta"]: oferta
        for oferta in get_ofertas_estudiante(db, datos.cod_estudiante, datos.cod_periodo)
    }
    for id_oferta in datos.ofertas:
        oferta = disponibles.get(id_oferta)
        if not oferta:
            raise HTTPException(status_code=422, detail="Una oferta no pertenece a la malla o período seleccionado.")
        if not oferta["disponible"]:
            raise HTTPException(
                status_code=409,
                detail=f"{oferta['cod_curso']} no puede matricularse: {oferta['motivo']}",
            )

    seleccion = [disponibles[id_oferta] for id_oferta in datos.ofertas]
    codigos = [item["cod_curso"] for item in seleccion]
    if len(codigos) != len(set(codigos)):
        raise HTTPException(status_code=409, detail="Seleccione solo una sección por curso.")
    sesiones_por_oferta = {}
    for item in seleccion:
        sesiones_por_oferta[item["id_oferta"]] = (
            db.query(models.HorarioCurso)
            .join(models.HorarioCabecera, models.HorarioCabecera.id_horario == models.HorarioCurso.id_horario)
            .filter(
                models.HorarioCabecera.cod_periodo == datos.cod_periodo,
                models.HorarioCurso.cod_curso == item["cod_curso"],
                models.HorarioCurso.cod_seccion == item["cod_seccion"],
            ).all()
        )
    for indice, izquierda in enumerate(seleccion):
        for derecha in seleccion[indice + 1:]:
            for sesion_a in sesiones_por_oferta[izquierda["id_oferta"]]:
                for sesion_b in sesiones_por_oferta[derecha["id_oferta"]]:
                    if (sesion_a.dia_semana == sesion_b.dia_semana
                            and sesion_a.hora_inicio < sesion_b.hora_fin
                            and sesion_a.hora_fin > sesion_b.hora_inicio):
                        raise HTTPException(
                            status_code=409,
                            detail=(f"Cruce de horario entre {izquierda['cod_curso']} sección {izquierda['cod_seccion']} "
                                    f"y {derecha['cod_curso']} sección {derecha['cod_seccion']} ({sesion_a.dia_semana})."),
                        )

    matricula = models.Matricula(
        cod_estudiante=estudiante.cod_estudiante, cod_periodo=datos.cod_periodo,
        cod_fac=estudiante.cod_fac, cod_esc=estudiante.cod_esc,
        corr_pe=estudiante.corr_pe, ciclo_matricula=estudiante.ciclo_actual,
        fecha_matricula=date.today(), estado="REGISTRADA",
    )
    db.add(matricula)
    db.flush()
    for id_oferta in datos.ofertas:
        db.add(models.MatriculaDetalle(
            id_matricula=matricula.id_matricula, id_oferta=id_oferta,
            resultado="MATRICULADO",
        ))
    estudiante.prematricula = ""
    _commit(db, "No se pudo registrar la matrícula por un conflicto académico.")
    return next(
        item for item in get_matriculas_estudiante(db, estudiante.cod_estudiante)
        if item["id_matricula"] == matricula.id_matricula
    )


def get_matriculas_estudiante(db: Session, codigo: str):
    if not db.query(models.Estudiante).filter_by(cod_estudiante=codigo).first():
        raise HTTPException(status_code=404, detail="El estudiante no existe.")
    matriculas = db.query(models.Matricula).filter_by(cod_estudiante=codigo).order_by(
        models.Matricula.cod_periodo.desc(),
    ).all()
    resultado = []
    for matricula in matriculas:
        detalles = (
            db.query(models.MatriculaDetalle, models.OfertaCurso, models.Curso, models.Docente)
            .join(models.OfertaCurso, models.OfertaCurso.id_oferta == models.MatriculaDetalle.id_oferta)
            .join(models.Curso, and_(
                models.Curso.cod_fac == models.OfertaCurso.cod_fac,
                models.Curso.cod_esc == models.OfertaCurso.cod_esc,
                models.Curso.corr_pe == models.OfertaCurso.corr_pe,
                models.Curso.cod_curso == models.OfertaCurso.cod_curso,
            ))
            .outerjoin(models.Docente, and_(
                models.Docente.cod_fac == models.OfertaCurso.cod_fac,
                models.Docente.cod_esc == models.OfertaCurso.cod_esc,
                models.Docente.cod_docente == models.OfertaCurso.cod_docente,
            ))
            .filter(models.MatriculaDetalle.id_matricula == matricula.id_matricula)
            .order_by(models.Curso.semestre, models.Curso.cod_curso)
            .all()
        )
        detalles_respuesta = [{
                "id_matricula": detalle.id_matricula, "id_oferta": detalle.id_oferta,
                "cod_periodo": oferta.cod_periodo, "cod_curso": curso.cod_curso,
                "den_curso": curso.den_curso, "semestre": curso.semestre,
                "cod_seccion": oferta.cod_seccion,
                "cod_docente": oferta.cod_docente,
                "docente_nombre": docente.apellidos_nombres if docente else "Por asignar",
                "cred": curso.cred,
                "nota_practicas": detalle.nota_practicas,
                "nota_parcial": detalle.nota_parcial,
                "nota_examen_final": detalle.nota_examen_final,
                "nota_final": detalle.nota_final,
                "resultado": detalle.resultado,
            } for detalle, oferta, curso, docente in detalles]
        calificados = [item for item in detalles_respuesta if item["nota_final"] is not None and item["resultado"] != "RETIRADO"]
        creditos_calificados = sum(item["cred"] for item in calificados)
        resultado.append({
            "id_matricula": matricula.id_matricula,
            "cod_estudiante": matricula.cod_estudiante,
            "cod_periodo": matricula.cod_periodo,
            "ciclo_matricula": matricula.ciclo_matricula,
            "fecha_matricula": matricula.fecha_matricula,
            "estado": matricula.estado,
            "total_creditos": sum(item["cred"] for item in detalles_respuesta if item["resultado"] != "RETIRADO"),
            "promedio_aritmetico": round(sum(item["nota_final"] for item in calificados) / len(calificados), 2) if calificados else None,
            "promedio_ponderado": round(sum(item["nota_final"] * item["cred"] for item in calificados) / creditos_calificados, 2) if creditos_calificados else None,
            "detalles": detalles_respuesta,
        })
    return resultado


def get_prematricula(db: Session, codigo: str):
    estudiante = db.query(models.Estudiante).filter_by(cod_estudiante=codigo).first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="El estudiante no existe.")
    if not estudiante.prematricula:
        return {"cod_periodo": "", "ofertas": []}
    try:
        datos = json.loads(estudiante.prematricula)
        return {"cod_periodo": str(datos.get("cod_periodo", "")), "ofertas": [int(x) for x in datos.get("ofertas", [])]}
    except (ValueError, TypeError, json.JSONDecodeError):
        return {"cod_periodo": "", "ofertas": []}


def guardar_prematricula(db: Session, codigo: str, datos: schemas.Prematricula):
    estudiante = db.query(models.Estudiante).filter_by(cod_estudiante=codigo).first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="El estudiante no existe.")
    ofertas = db.query(models.OfertaCurso).filter(models.OfertaCurso.id_oferta.in_(datos.ofertas)).all() if datos.ofertas else []
    if len(ofertas) != len(set(datos.ofertas)) or any(
        oferta.cod_periodo != datos.cod_periodo
        or oferta.corr_pe != estudiante.corr_pe
        or oferta.cod_fac != estudiante.cod_fac
        or oferta.cod_esc != estudiante.cod_esc
        for oferta in ofertas
    ):
        raise HTTPException(status_code=422, detail="La prematrícula contiene una oferta que no pertenece al estudiante o período.")
    codigos = [oferta.cod_curso for oferta in ofertas]
    if len(codigos) != len(set(codigos)):
        raise HTTPException(status_code=409, detail="La prematrícula solo admite una sección por curso.")
    estudiante.prematricula = json.dumps({"cod_periodo": datos.cod_periodo, "ofertas": datos.ofertas})
    _commit(db, "No se pudo guardar la prematrícula.")
    return {"mensaje": "Prematrícula guardada como guía. La matrícula oficial no fue modificada."}


def registrar_resultado(
    db: Session, id_matricula: int, id_oferta: int, datos: schemas.ResultadoUpdate,
):
    _aplicar_resultado(db, id_matricula, id_oferta, datos)
    _cerrar_matricula_si_corresponde(db, id_matricula)
    _commit(db, "No se pudo actualizar el resultado académico.")
    return {"mensaje": "Resultado académico actualizado correctamente."}


def _aplicar_resultado(
    db: Session, id_matricula: int, id_oferta: int, datos: schemas.ResultadoUpdate,
):
    detalle = db.query(models.MatriculaDetalle).filter_by(
        id_matricula=id_matricula, id_oferta=id_oferta,
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="El curso matriculado no existe.")
    if datos.resultado == "RETIRADO":
        detalle.nota_practicas = None
        detalle.nota_parcial = None
        detalle.nota_examen_final = None
        detalle.nota_final = None
        detalle.resultado = "RETIRADO"
        return

    detalle.nota_practicas = datos.nota_practicas
    detalle.nota_parcial = datos.nota_parcial
    detalle.nota_examen_final = datos.nota_examen_final
    componentes = (datos.nota_practicas, datos.nota_parcial, datos.nota_examen_final)
    if all(nota is not None for nota in componentes):
        promedio = int(
            datos.nota_practicas * 0.40
            + datos.nota_parcial * 0.30
            + datos.nota_examen_final * 0.30
            + 0.5
        )
        detalle.nota_final = promedio
        detalle.resultado = "APROBADO" if promedio >= 11 else "DESAPROBADO"
    elif datos.nota_final is not None and all(nota is None for nota in componentes):
        # Compatibilidad con registros anteriores que solo guardaban una nota final.
        detalle.nota_final = datos.nota_final
        detalle.resultado = "APROBADO" if datos.nota_final >= 11 else "DESAPROBADO"
    else:
        detalle.nota_final = None
        detalle.resultado = "MATRICULADO"


def registrar_resultados_lote(
    db: Session, id_matricula: int, datos: schemas.ResultadosLoteUpdate,
):
    ids = [item.id_oferta for item in datos.resultados]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="No se puede repetir un curso en la actualización.")
    for item in datos.resultados:
        _aplicar_resultado(db, id_matricula, item.id_oferta, item)
    _cerrar_matricula_si_corresponde(db, id_matricula)
    _commit(db, "No se pudieron guardar todos los resultados académicos.")
    return {"mensaje": "Notas y resultados guardados correctamente."}


def _cerrar_matricula_si_corresponde(db: Session, id_matricula: int) -> None:
    matricula = db.query(models.Matricula).filter_by(id_matricula=id_matricula).first()
    if not matricula or matricula.estado == "CERRADA":
        return
    detalles = db.query(models.MatriculaDetalle).filter_by(id_matricula=id_matricula).all()
    if not detalles or any(item.resultado == "MATRICULADO" for item in detalles):
        return
    matricula.estado = "CERRADA"
    if any(item.resultado == "APROBADO" for item in detalles):
        estudiante = db.query(models.Estudiante).filter_by(
            cod_estudiante=matricula.cod_estudiante,
        ).first()
        if estudiante and estudiante.ciclo_actual < 10:
            estudiante.ciclo_actual += 1


def _usuario_dict(usuario: models.Usuario):
    return {
        "id_usuario": usuario.id_usuario,
        "nombre_usuario": usuario.nombre_usuario,
        "nombre_mostrar": usuario.nombre_mostrar,
        "cod_estudiante": usuario.cod_estudiante,
        "perfiles": sorted(perfil.codigo for perfil in usuario.perfiles),
        "activo": usuario.activo,
    }


def autenticar(db: Session, nombre_usuario: str, clave: str):
    usuario = db.query(models.Usuario).filter(
        func.lower(models.Usuario.nombre_usuario) == nombre_usuario.strip().lower(),
    ).first()
    if not usuario or not usuario.activo or not auth.verify_password(clave, usuario.clave_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    perfiles = sorted(perfil.codigo for perfil in usuario.perfiles)
    if not perfiles:
        raise HTTPException(status_code=403, detail="El usuario no tiene perfiles asignados.")
    perfil_activo = auth.PERFIL_ADMIN if auth.PERFIL_ADMIN in perfiles else perfiles[0]
    return usuario, perfil_activo


def get_usuarios(db: Session):
    return [_usuario_dict(usuario) for usuario in db.query(models.Usuario).order_by(
        models.Usuario.nombre_mostrar,
    ).all()]


def _resolver_perfiles(db: Session, codigos: list[str]):
    normalizados = sorted({codigo.strip().upper() for codigo in codigos})
    perfiles = db.query(models.Perfil).filter(models.Perfil.codigo.in_(normalizados)).all()
    if len(perfiles) != len(normalizados):
        raise HTTPException(status_code=422, detail="Uno o más perfiles no son válidos.")
    return perfiles


def _validar_vinculo_estudiante(db: Session, codigo: str | None, perfiles: list[models.Perfil]):
    tiene_perfil = any(
        "MATRICULA_PROPIA" in perfil.permisos.split(",") for perfil in perfiles
    )
    if tiene_perfil and not codigo:
        raise HTTPException(status_code=422, detail="El perfil Estudiante requiere vincular un estudiante.")
    if codigo and not db.query(models.Estudiante).filter_by(cod_estudiante=codigo).first():
        raise HTTPException(status_code=404, detail="El estudiante que desea vincular no existe.")


def crear_usuario(db: Session, datos: schemas.UsuarioCreate):
    perfiles = _resolver_perfiles(db, datos.perfiles)
    codigo = datos.cod_estudiante.strip().upper() if datos.cod_estudiante else None
    _validar_vinculo_estudiante(db, codigo, perfiles)
    estudiante = db.query(models.Estudiante).filter_by(cod_estudiante=codigo).first() if codigo else None
    usuario = models.Usuario(
        nombre_usuario=datos.nombre_usuario.strip().lower(),
        clave_hash=auth.hash_password(estudiante.dni if estudiante else datos.clave),
        nombre_mostrar=datos.nombre_mostrar.strip(),
        cod_estudiante=codigo,
        activo=datos.activo,
    )
    usuario.perfiles = perfiles
    db.add(usuario)
    _commit(db, "El nombre de usuario o estudiante vinculado ya pertenece a otra cuenta.")
    db.refresh(usuario)
    return _usuario_dict(usuario)


def editar_usuario(db: Session, id_usuario: int, datos: schemas.UsuarioUpdate):
    usuario = db.query(models.Usuario).filter_by(id_usuario=id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="El usuario no existe.")
    perfiles = _resolver_perfiles(db, datos.perfiles)
    codigo = datos.cod_estudiante.strip().upper() if datos.cod_estudiante else None
    _validar_vinculo_estudiante(db, codigo, perfiles)
    usuario.nombre_mostrar = datos.nombre_mostrar.strip()
    usuario.cod_estudiante = codigo
    usuario.activo = datos.activo
    usuario.perfiles = perfiles
    estudiante = db.query(models.Estudiante).filter_by(cod_estudiante=codigo).first() if codigo else None
    if estudiante:
        usuario.clave_hash = auth.hash_password(estudiante.dni)
    elif datos.clave:
        usuario.clave_hash = auth.hash_password(datos.clave)
    _commit(db, "El estudiante vinculado ya pertenece a otra cuenta.")
    return _usuario_dict(usuario)


def eliminar_usuario(db: Session, id_usuario: int, actual_id: int):
    if id_usuario == actual_id:
        raise HTTPException(status_code=409, detail="No puede eliminar su propia cuenta activa.")
    usuario = db.query(models.Usuario).filter_by(id_usuario=id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="El usuario no existe.")
    nombre = usuario.nombre_usuario
    db.delete(usuario)
    _commit(db, "No se pudo eliminar el usuario.")
    return {"mensaje": f"Usuario {nombre} eliminado correctamente."}


def get_perfiles(db: Session):
    filas = (
        db.query(models.Perfil, func.count(models.UsuarioPerfil.id_usuario))
        .outerjoin(
            models.UsuarioPerfil,
            models.UsuarioPerfil.id_perfil == models.Perfil.id_perfil,
        )
        .group_by(models.Perfil.id_perfil)
        .order_by(models.Perfil.id_perfil)
        .all()
    )
    return [{
        "id_perfil": perfil.id_perfil,
        "codigo": perfil.codigo,
        "nombre": perfil.nombre,
        "permisos": sorted(item for item in perfil.permisos.split(",") if item),
        "total_usuarios": total,
    } for perfil, total in filas]


def editar_perfil(db: Session, id_perfil: int, datos: schemas.PerfilUpdate):
    perfil = db.query(models.Perfil).filter_by(id_perfil=id_perfil).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="El perfil no existe.")
    perfil.nombre = datos.nombre
    permisos = sorted(set(datos.permisos))
    invalidos = set(permisos) - auth.PERMISOS_VALIDOS
    if invalidos:
        raise HTTPException(status_code=422, detail="Uno o más permisos no son válidos.")
    perfil.permisos = ",".join(permisos)
    _commit(db, "Ya existe otro perfil con ese nombre.")
    return next(item for item in get_perfiles(db) if item["id_perfil"] == id_perfil)


def crear_perfil(db: Session, datos: schemas.PerfilCreate):
    permisos = sorted(set(datos.permisos))
    if set(permisos) - auth.PERMISOS_VALIDOS:
        raise HTTPException(status_code=422, detail="Uno o más permisos no son válidos.")
    perfil = models.Perfil(
        codigo=datos.codigo, nombre=datos.nombre, permisos=",".join(permisos),
    )
    db.add(perfil)
    _commit(db, "El código o nombre del perfil ya existe.")
    db.refresh(perfil)
    return next(item for item in get_perfiles(db) if item["id_perfil"] == perfil.id_perfil)


def eliminar_perfil(db: Session, id_perfil: int):
    perfil = db.query(models.Perfil).filter_by(id_perfil=id_perfil).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="El perfil no existe.")
    if perfil.codigo in {auth.PERFIL_ADMIN, auth.PERFIL_ESTUDIANTE}:
        raise HTTPException(status_code=409, detail="Los perfiles institucionales base no se pueden eliminar.")
    if db.query(models.UsuarioPerfil).filter_by(id_perfil=id_perfil).first():
        raise HTTPException(status_code=409, detail="No se puede eliminar un perfil asignado a usuarios.")
    nombre = perfil.nombre
    db.delete(perfil)
    _commit(db, "No se pudo eliminar el perfil.")
    return {"mensaje": f"Perfil {nombre} eliminado correctamente."}
