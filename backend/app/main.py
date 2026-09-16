import os
from typing import List

from fastapi import Depends, FastAPI, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import engine, get_db


models.Base.metadata.create_all(bind=engine)

cors_origins = ["http://localhost:4200", "http://127.0.0.1:4200"]
cors_origins.extend(
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
)

app = FastAPI(
    title="Sistema de Gestión Académica FIIS",
    description="Consulta de planes, prerrequisitos, programación académica y plana docente.",
    version="3.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "API de Gestión Académica FIIS operativa", "version": "3.0.0"}


@app.get("/facultades/", response_model=List[schemas.Facultad])
def read_facultades(db: Session = Depends(get_db)):
    return crud.get_facultades(db)


@app.get("/escuelas/", response_model=List[schemas.Escuela])
def read_escuelas(cod_fac: int | None = None, db: Session = Depends(get_db)):
    return crud.get_escuelas(db, cod_fac)


@app.get("/docentes/", response_model=List[schemas.Docente])
def read_docentes(
    buscar: str | None = None,
    categoria: str | None = None,
    db: Session = Depends(get_db),
):
    return crud.get_docentes(db, buscar, categoria)


@app.get("/planes/", response_model=List[schemas.PlanEstudio])
def read_planes(cod_fac: int | None = None, cod_esc: int | None = None, db: Session = Depends(get_db)):
    return crud.get_planes(db, cod_fac, cod_esc)


@app.get("/cursos/", response_model=List[schemas.Curso])
def read_cursos(
    cod_fac: int | None = None,
    cod_esc: int | None = None,
    corr_pe: int | None = None,
    semestre: int | None = Query(default=None, ge=1, le=10),
    buscar: str | None = None,
    db: Session = Depends(get_db),
):
    return crud.get_cursos(db, cod_fac, cod_esc, corr_pe, semestre, buscar)


@app.get("/periodos/", response_model=List[schemas.PeriodoAcademico])
def read_periodos(db: Session = Depends(get_db)):
    return crud.get_periodos(db)


@app.get("/programacion/", response_model=List[schemas.ProgramacionHorario])
def read_programacion(
    corr_pe: int | None = None,
    cod_periodo: str | None = None,
    semestre: int | None = Query(default=None, ge=1, le=10),
    db: Session = Depends(get_db),
):
    return crud.get_programacion(db, corr_pe, cod_periodo, semestre)


@app.get("/horarios/", response_model=List[schemas.HorarioDisponible])
def read_horarios(
    corr_pe: int | None = None,
    cod_periodo: str | None = None,
    semestre: int | None = Query(default=None, ge=1, le=10),
    db: Session = Depends(get_db),
):
    return crud.get_horarios_disponibles(db, corr_pe, cod_periodo, semestre)


@app.get("/semestres/", response_model=List[int])
def read_semestres(
    corr_pe: int,
    cod_fac: int = 1,
    cod_esc: int = 1,
    db: Session = Depends(get_db),
):
    return crud.get_semestres(db, corr_pe, cod_fac, cod_esc)


@app.get("/cursos/{cod_curso}/detalle", response_model=schemas.CursoDetalle)
def read_curso_detalle(
    cod_curso: str,
    corr_pe: int,
    cod_fac: int = 1,
    cod_esc: int = 1,
    db: Session = Depends(get_db),
):
    return crud.get_curso_detalle(db, corr_pe, cod_curso, cod_fac, cod_esc)


@app.get("/resumen-semestre/", response_model=schemas.ResumenSemestre)
def read_resumen_semestre(
    corr_pe: int,
    semestre: int = Query(ge=1, le=10),
    cod_fac: int = 1,
    cod_esc: int = 1,
    db: Session = Depends(get_db),
):
    return crud.get_resumen_semestre(db, corr_pe, semestre, cod_fac, cod_esc)


@app.post("/cursos/", response_model=schemas.Curso, status_code=status.HTTP_201_CREATED)
def create_curso(datos: schemas.CursoCreate, db: Session = Depends(get_db)):
    return crud.crear_curso(db, datos)


@app.put("/cursos/{cod_curso}", response_model=schemas.Curso)
def update_curso(
    cod_curso: str,
    corr_pe: int,
    datos: schemas.CursoUpdate,
    cod_fac: int = 1,
    cod_esc: int = 1,
    db: Session = Depends(get_db),
):
    return crud.editar_curso(db, corr_pe, cod_curso, datos, cod_fac, cod_esc)


@app.delete("/cursos/{cod_curso}", response_model=schemas.Mensaje)
def delete_curso(
    cod_curso: str,
    corr_pe: int,
    cod_fac: int = 1,
    cod_esc: int = 1,
    db: Session = Depends(get_db),
):
    return crud.eliminar_curso(db, corr_pe, cod_curso, cod_fac, cod_esc)


@app.post("/prerrequisitos/", response_model=schemas.Mensaje, status_code=status.HTTP_201_CREATED)
def create_prerequisito(datos: schemas.PrerequisitoCreate, db: Session = Depends(get_db)):
    return crud.agregar_prerequisito(db, datos)


@app.delete(
    "/prerrequisitos/{corr_pe}/{cod_curso}/{cod_requisito}",
    response_model=schemas.Mensaje,
)
def delete_prerequisito(
    corr_pe: int,
    cod_curso: str,
    cod_requisito: str,
    cod_fac: int = 1,
    cod_esc: int = 1,
    db: Session = Depends(get_db),
):
    return crud.retirar_prerequisito(
        db, corr_pe, cod_curso, cod_requisito, cod_fac, cod_esc,
    )


@app.post("/sesiones/", response_model=schemas.Mensaje, status_code=status.HTTP_201_CREATED)
def create_sesion(datos: schemas.SesionCreate, db: Session = Depends(get_db)):
    return crud.crear_sesion(db, datos)


@app.put("/sesiones/", response_model=schemas.Mensaje)
def update_sesion(datos: schemas.SesionEdicion, db: Session = Depends(get_db)):
    return crud.editar_sesion(db, datos)
