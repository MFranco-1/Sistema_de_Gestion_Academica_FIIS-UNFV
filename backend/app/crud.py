from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, not_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas


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
