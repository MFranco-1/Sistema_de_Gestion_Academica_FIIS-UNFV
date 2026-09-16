from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Facultad(BaseModel):
    cod_fac: int
    den_fac: str
    class Config:
        from_attributes = True


class Escuela(BaseModel):
    cod_fac: int
    cod_esc: int
    den_escuela: str
    class Config:
        from_attributes = True


class Docente(BaseModel):
    cod_fac: int
    cod_esc: int
    cod_docente: str
    apellidos_nombres: str
    categoria: str
    dedicacion: str
    departamento: str
    fuente: str
    class Config:
        from_attributes = True


class PlanEstudio(BaseModel):
    cod_fac: int
    cod_esc: int
    corr_pe: int
    den_plan: str
    anio_plan: int
    fecha_vigencia: date
    fecha_baja: Optional[date] = None
    vigente: bool
    total_cursos: int = 0
    total_creditos: int = 0
    class Config:
        from_attributes = True


class Curso(BaseModel):
    cod_fac: int
    cod_esc: int
    corr_pe: int
    cod_curso: str
    den_curso: str
    semestre: int
    ht: int
    hp: int
    cred: int
    tipo_curso: str
    prerrequisitos_nombres: str = "Ninguno"
    class Config:
        from_attributes = True


class PeriodoAcademico(BaseModel):
    cod_periodo: str
    den_periodo: str
    fecha_inicio: date
    fecha_fin: date
    activo: bool
    class Config:
        from_attributes = True


class ProgramacionHorario(BaseModel):
    id_horario: int
    cod_periodo: str
    corr_pe: int
    den_plan: str
    semestre_corr: int
    semestre_desc: str
    cod_curso: str
    den_curso: str
    cod_seccion: str
    tipo_sesion: str
    dia_semana: str
    hora_inicio: time
    hora_fin: time
    aula: str


class HorarioDisponible(BaseModel):
    id_horario: int
    cod_periodo: str
    corr_pe: int
    semestre_corr: int
    semestre_desc: str


class CursoRelacionado(BaseModel):
    cod_curso: str
    den_curso: str
    semestre: int


class CursoDetalle(Curso):
    den_plan: str
    anio_plan: int
    prerrequisitos: list[CursoRelacionado] = []
    cursos_dependientes: list[CursoRelacionado] = []


class ResumenSemestre(BaseModel):
    corr_pe: int
    semestre: int
    total_cursos: int
    total_creditos: int
    horas_teoricas: int
    horas_practicas: int
    cursos_obligatorios: int
    cursos_electivos: int
    cursos_con_prerrequisitos: int
    cursos_sin_prerrequisitos: int


class CursoCreate(BaseModel):
    cod_fac: int = 1
    cod_esc: int = 1
    corr_pe: int
    cod_curso: str = Field(min_length=1, max_length=20)
    den_curso: str = Field(min_length=1, max_length=160)
    semestre: int = Field(ge=1, le=10)
    ht: int = Field(ge=0)
    hp: int = Field(ge=0)
    cred: int = Field(gt=0)
    tipo_curso: str

    @field_validator("cod_curso")
    @classmethod
    def limpiar_codigo(cls, valor: str) -> str:
        return valor.strip().upper()

    @field_validator("den_curso")
    @classmethod
    def limpiar_nombre(cls, valor: str) -> str:
        return valor.strip()

    @field_validator("tipo_curso")
    @classmethod
    def validar_tipo(cls, valor: str) -> str:
        valor = valor.upper()
        if valor not in {"OBLIGATORIO", "ELECTIVO"}:
            raise ValueError("El tipo de curso debe ser OBLIGATORIO o ELECTIVO.")
        return valor


class CursoUpdate(BaseModel):
    den_curso: str = Field(min_length=1, max_length=160)
    semestre: int = Field(ge=1, le=10)
    ht: int = Field(ge=0)
    hp: int = Field(ge=0)
    cred: int = Field(gt=0)
    tipo_curso: str

    @field_validator("den_curso")
    @classmethod
    def limpiar_nombre(cls, valor: str) -> str:
        return valor.strip()

    @field_validator("tipo_curso")
    @classmethod
    def validar_tipo(cls, valor: str) -> str:
        valor = valor.strip().upper()
        if valor not in {"OBLIGATORIO", "ELECTIVO"}:
            raise ValueError("El tipo de curso debe ser OBLIGATORIO o ELECTIVO.")
        return valor


class PrerequisitoCreate(BaseModel):
    cod_fac: int = 1
    cod_esc: int = 1
    corr_pe: int
    cod_curso: str
    cod_curso_prerequisito: str


class SesionCreate(BaseModel):
    id_horario: int
    semestre_corr: int = Field(ge=1, le=10)
    cod_curso: str
    cod_seccion: str
    tipo_sesion: str
    cod_fac: int = 1
    cod_esc: int = 1
    corr_pe: int
    dia_semana: str
    hora_inicio: time
    hora_fin: time
    aula: str

    @field_validator("cod_curso", "cod_seccion", "tipo_sesion", "dia_semana", "aula")
    @classmethod
    def normalizar(cls, valor: str) -> str:
        return valor.strip().upper()

    @field_validator("tipo_sesion")
    @classmethod
    def validar_tipo_sesion(cls, valor: str) -> str:
        if valor not in {"T", "P"}:
            raise ValueError("El tipo de sesión debe ser T o P.")
        return valor

    @field_validator("dia_semana")
    @classmethod
    def validar_dia(cls, valor: str) -> str:
        if valor not in {"LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"}:
            raise ValueError("El día de la semana no es válido.")
        return valor


class SesionLocator(BaseModel):
    id_horario: int
    semestre_corr: int
    cod_curso: str
    cod_seccion: str
    tipo_sesion: str
    dia_semana: str
    hora_inicio: time


class SesionEdicion(BaseModel):
    original: SesionLocator
    sesion: SesionCreate


class Mensaje(BaseModel):
    mensaje: str
