import os
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import auth, crud, models, schemas
from app.database import SessionLocal, engine, get_db


models.Base.metadata.create_all(bind=engine)
with engine.begin() as migration_connection:
    migration_connection.exec_driver_sql(
        "ALTER TABLE perfil ADD COLUMN IF NOT EXISTS permisos VARCHAR(500) NOT NULL DEFAULT ''"
    )
with SessionLocal() as startup_db:
    auth.ensure_security_data(startup_db)

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


def _sesion_dict(usuario, perfil_activo: str):
    return {
        "id_usuario": usuario.id_usuario,
        "nombre_usuario": usuario.nombre_usuario,
        "nombre_mostrar": usuario.nombre_mostrar,
        "cod_estudiante": usuario.cod_estudiante,
        "perfil_activo": perfil_activo,
        "perfiles": sorted(perfil.codigo for perfil in usuario.perfiles),
        "nombres_perfiles": {perfil.codigo: perfil.nombre for perfil in usuario.perfiles},
        "permisos": sorted({
            permiso for perfil in usuario.perfiles if perfil.codigo == perfil_activo
            for permiso in perfil.permisos.split(",") if permiso
        }),
    }


@app.post("/auth/login", response_model=schemas.LoginResponse)
def login(datos: schemas.LoginRequest, db: Session = Depends(get_db)):
    usuario, perfil_activo = crud.autenticar(db, datos.nombre_usuario, datos.clave)
    return {
        "token": auth.create_token(usuario, perfil_activo),
        "usuario": _sesion_dict(usuario, perfil_activo),
    }


@app.get("/auth/me", response_model=schemas.UsuarioSesion)
def me(actual: auth.UsuarioActual = Depends(auth.get_current_user)):
    return actual.__dict__


@app.post("/auth/cambiar-perfil", response_model=schemas.LoginResponse)
def cambiar_perfil(
    datos: schemas.CambioPerfil,
    actual: auth.UsuarioActual = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if datos.perfil not in actual.perfiles:
        raise HTTPException(status_code=403, detail="El usuario no tiene asignado ese perfil.")
    usuario = db.query(models.Usuario).filter_by(id_usuario=actual.id_usuario).one()
    return {
        "token": auth.create_token(usuario, datos.perfil),
        "usuario": _sesion_dict(usuario, datos.perfil),
    }


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
def create_curso(datos: schemas.CursoCreate, db: Session = Depends(get_db), _=Depends(auth.require_permission("MANTENIMIENTO_ACADEMICO"))):
    return crud.crear_curso(db, datos)


@app.put("/cursos/{cod_curso}", response_model=schemas.Curso)
def update_curso(
    cod_curso: str,
    corr_pe: int,
    datos: schemas.CursoUpdate,
    cod_fac: int = 1,
    cod_esc: int = 1,
    db: Session = Depends(get_db),
    _: auth.UsuarioActual = Depends(auth.require_permission("MANTENIMIENTO_ACADEMICO")),
):
    return crud.editar_curso(db, corr_pe, cod_curso, datos, cod_fac, cod_esc)


@app.delete("/cursos/{cod_curso}", response_model=schemas.Mensaje)
def delete_curso(
    cod_curso: str,
    corr_pe: int,
    cod_fac: int = 1,
    cod_esc: int = 1,
    db: Session = Depends(get_db),
    _: auth.UsuarioActual = Depends(auth.require_permission("MANTENIMIENTO_ACADEMICO")),
):
    return crud.eliminar_curso(db, corr_pe, cod_curso, cod_fac, cod_esc)


@app.post("/prerrequisitos/", response_model=schemas.Mensaje, status_code=status.HTTP_201_CREATED)
def create_prerequisito(datos: schemas.PrerequisitoCreate, db: Session = Depends(get_db), _=Depends(auth.require_permission("MANTENIMIENTO_ACADEMICO"))):
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
    _: auth.UsuarioActual = Depends(auth.require_permission("MANTENIMIENTO_ACADEMICO")),
):
    return crud.retirar_prerequisito(
        db, corr_pe, cod_curso, cod_requisito, cod_fac, cod_esc,
    )


@app.post("/sesiones/", response_model=schemas.Mensaje, status_code=status.HTTP_201_CREATED)
def create_sesion(datos: schemas.SesionCreate, db: Session = Depends(get_db), _=Depends(auth.require_permission("MANTENIMIENTO_ACADEMICO"))):
    return crud.crear_sesion(db, datos)


@app.put("/sesiones/", response_model=schemas.Mensaje)
def update_sesion(datos: schemas.SesionEdicion, db: Session = Depends(get_db), _=Depends(auth.require_permission("MANTENIMIENTO_ACADEMICO"))):
    return crud.editar_sesion(db, datos)


@app.get("/estudiantes/", response_model=List[schemas.Estudiante])
def read_estudiantes(buscar: str | None = None, db: Session = Depends(get_db), _=Depends(auth.require_any_permission("GESTION_ESTUDIANTES", "GESTION_MATRICULAS", "GESTION_USUARIOS"))):
    return crud.get_estudiantes(db, buscar)


@app.get("/estudiantes/me", response_model=schemas.Estudiante)
def read_mi_estudiante(
    actual: auth.UsuarioActual = Depends(auth.require_student),
    db: Session = Depends(get_db),
):
    estudiantes = crud.get_estudiantes(db, actual.cod_estudiante)
    if not estudiantes:
        raise HTTPException(status_code=404, detail="No se encontró la ficha del estudiante.")
    return estudiantes[0]


@app.post("/estudiantes/", response_model=schemas.Estudiante, status_code=status.HTTP_201_CREATED)
def create_estudiante(datos: schemas.EstudianteCreate, db: Session = Depends(get_db), _=Depends(auth.require_permission("GESTION_ESTUDIANTES"))):
    return crud.crear_estudiante(db, datos)


@app.put("/estudiantes/{codigo}", response_model=schemas.Estudiante)
def update_estudiante(
    codigo: str, datos: schemas.EstudianteUpdate, db: Session = Depends(get_db),
    _: auth.UsuarioActual = Depends(auth.require_permission("GESTION_ESTUDIANTES")),
):
    return crud.editar_estudiante(db, codigo, datos)


@app.delete("/estudiantes/{codigo}", response_model=schemas.Mensaje)
def delete_estudiante(codigo: str, db: Session = Depends(get_db), _=Depends(auth.require_permission("GESTION_ESTUDIANTES"))):
    return crud.eliminar_estudiante(db, codigo)


@app.get("/estudiantes/{codigo}/ofertas", response_model=List[schemas.OfertaCurso])
def read_ofertas_estudiante(
    codigo: str, cod_periodo: str,
    actual: auth.UsuarioActual = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if "GESTION_MATRICULAS" not in actual.permisos and (
        "MATRICULA_PROPIA" not in actual.permisos or actual.cod_estudiante != codigo
    ):
        raise HTTPException(status_code=403, detail="Solo puede consultar sus propias ofertas.")
    return crud.get_ofertas_estudiante(db, codigo, cod_periodo)


@app.get("/estudiantes/{codigo}/matriculas", response_model=List[schemas.MatriculaResumen])
def read_matriculas_estudiante(
    codigo: str,
    actual: auth.UsuarioActual = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if "GESTION_MATRICULAS" not in actual.permisos and (
        "MATRICULA_PROPIA" not in actual.permisos or actual.cod_estudiante != codigo
    ):
        raise HTTPException(status_code=403, detail="Solo puede consultar su propio historial.")
    return crud.get_matriculas_estudiante(db, codigo)


@app.post("/matriculas/", response_model=schemas.MatriculaResumen, status_code=status.HTTP_201_CREATED)
def create_matricula(
    datos: schemas.MatriculaCreate,
    actual: auth.UsuarioActual = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if "GESTION_MATRICULAS" not in actual.permisos and (
        "MATRICULA_PROPIA" not in actual.permisos
        or actual.cod_estudiante != datos.cod_estudiante
    ):
        raise HTTPException(status_code=403, detail="Solo puede registrar su propia matrícula.")
    return crud.crear_matricula(db, datos)


@app.put(
    "/matriculas/{id_matricula}/ofertas/{id_oferta}/resultado",
    response_model=schemas.Mensaje,
)
def update_resultado(
    id_matricula: int, id_oferta: int, datos: schemas.ResultadoUpdate,
    db: Session = Depends(get_db),
    _: auth.UsuarioActual = Depends(auth.require_permission("GESTION_MATRICULAS")),
):
    return crud.registrar_resultado(db, id_matricula, id_oferta, datos)


@app.put("/matriculas/{id_matricula}/resultados", response_model=schemas.Mensaje)
def update_resultados_lote(
    id_matricula: int, datos: schemas.ResultadosLoteUpdate,
    db: Session = Depends(get_db),
    _: auth.UsuarioActual = Depends(auth.require_permission("GESTION_MATRICULAS")),
):
    return crud.registrar_resultados_lote(db, id_matricula, datos)


@app.get("/usuarios/", response_model=List[schemas.UsuarioAdministracion])
def read_usuarios(db: Session = Depends(get_db), _=Depends(auth.require_permission("GESTION_USUARIOS"))):
    return crud.get_usuarios(db)


@app.post("/usuarios/", response_model=schemas.UsuarioAdministracion, status_code=status.HTTP_201_CREATED)
def create_usuario(datos: schemas.UsuarioCreate, db: Session = Depends(get_db), _=Depends(auth.require_permission("GESTION_USUARIOS"))):
    return crud.crear_usuario(db, datos)


@app.put("/usuarios/{id_usuario}", response_model=schemas.UsuarioAdministracion)
def update_usuario(
    id_usuario: int, datos: schemas.UsuarioUpdate,
    db: Session = Depends(get_db), _=Depends(auth.require_permission("GESTION_USUARIOS")),
):
    return crud.editar_usuario(db, id_usuario, datos)


@app.delete("/usuarios/{id_usuario}", response_model=schemas.Mensaje)
def delete_usuario(
    id_usuario: int, db: Session = Depends(get_db),
    actual: auth.UsuarioActual = Depends(auth.require_permission("GESTION_USUARIOS")),
):
    return crud.eliminar_usuario(db, id_usuario, actual.id_usuario)


@app.get("/perfiles/", response_model=List[schemas.PerfilAdministracion])
def read_perfiles(db: Session = Depends(get_db), _=Depends(auth.require_any_permission("GESTION_PERFILES", "GESTION_USUARIOS"))):
    return crud.get_perfiles(db)


@app.put("/perfiles/{id_perfil}", response_model=schemas.PerfilAdministracion)
def update_perfil(
    id_perfil: int, datos: schemas.PerfilUpdate,
    db: Session = Depends(get_db), _=Depends(auth.require_permission("GESTION_PERFILES")),
):
    return crud.editar_perfil(db, id_perfil, datos)


@app.post("/perfiles/", response_model=schemas.PerfilAdministracion, status_code=status.HTTP_201_CREATED)
def create_perfil(
    datos: schemas.PerfilCreate, db: Session = Depends(get_db),
    _=Depends(auth.require_permission("GESTION_PERFILES")),
):
    return crud.crear_perfil(db, datos)


@app.delete("/perfiles/{id_perfil}", response_model=schemas.Mensaje)
def delete_perfil(
    id_perfil: int, db: Session = Depends(get_db),
    _=Depends(auth.require_permission("GESTION_PERFILES")),
):
    return crud.eliminar_perfil(db, id_perfil)
