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
    anio: int
    tipo_periodo: str
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


class EstudianteBase(BaseModel):
    dni: str = Field(pattern=r"^\d{8}$")
    apellidos_nombres: str = Field(min_length=3, max_length=160)
    correo: str = Field(min_length=5, max_length=120)
    cod_fac: int = 1
    cod_esc: int = 1
    corr_pe: int
    ciclo_actual: int = Field(ge=1, le=10)
    estado: str = "ACTIVO"

    @field_validator("apellidos_nombres", "correo")
    @classmethod
    def limpiar_texto(cls, valor: str) -> str:
        return valor.strip()

    @field_validator("estado")
    @classmethod
    def validar_estado_estudiante(cls, valor: str) -> str:
        valor = valor.strip().upper()
        if valor not in {"ACTIVO", "EGRESADO", "RETIRADO"}:
            raise ValueError("El estado del estudiante no es válido.")
        return valor


class EstudianteCreate(EstudianteBase):
    cod_estudiante: str = Field(pattern=r"^\d{10}$")

    @field_validator("cod_estudiante")
    @classmethod
    def limpiar_codigo(cls, valor: str) -> str:
        return valor.strip().upper()


class EstudianteUpdate(EstudianteBase):
    pass


class Estudiante(EstudianteBase):
    # Las altas nuevas exigen 10 dígitos. La salida tolera registros heredados
    # para que uno antiguo no impida listar y administrar a todos los alumnos.
    cod_estudiante: str
    den_plan: str = ""
    anio_ingreso: int = 0
    creditos_aprobados: int = 0
    creditos_matriculados: int = 0
    class Config:
        from_attributes = True


class OfertaCurso(BaseModel):
    id_oferta: int
    cod_periodo: str
    corr_pe: int
    cod_curso: str
    den_curso: str
    semestre: int
    cred: int
    cod_seccion: str
    vacantes: int
    matriculados: int
    vacantes_disponibles: int
    disponible: bool
    motivo: str = ""
    horario_resumen: str = "Horario pendiente"


class OfertaSeccionCreate(BaseModel):
    cod_periodo: str
    corr_pe: int
    cod_curso: str
    cod_seccion: str = Field(min_length=1, max_length=10)
    vacantes: int = Field(gt=0, le=100)
    cod_fac: int = 1
    cod_esc: int = 1

    @field_validator("cod_curso", "cod_seccion")
    @classmethod
    def normalizar_oferta(cls, valor: str) -> str:
        return valor.strip().upper()


class MatriculaCreate(BaseModel):
    cod_estudiante: str
    cod_periodo: str
    ofertas: list[int] = Field(min_length=1)


class ResultadoUpdate(BaseModel):
    nota_final: Optional[int] = Field(default=None, ge=0, le=20)
    resultado: str

    @field_validator("resultado")
    @classmethod
    def validar_resultado(cls, valor: str) -> str:
        valor = valor.strip().upper()
        if valor not in {"MATRICULADO", "APROBADO", "DESAPROBADO", "RETIRADO"}:
            raise ValueError("El resultado académico no es válido.")
        return valor


class ResultadoLoteItem(ResultadoUpdate):
    id_oferta: int


class ResultadosLoteUpdate(BaseModel):
    resultados: list[ResultadoLoteItem] = Field(min_length=1)


class MatriculaDetalle(BaseModel):
    id_matricula: int
    id_oferta: int
    cod_periodo: str
    cod_curso: str
    den_curso: str
    semestre: int
    cod_seccion: str
    nota_final: Optional[int] = None
    resultado: str


class MatriculaResumen(BaseModel):
    id_matricula: int
    cod_estudiante: str
    cod_periodo: str
    ciclo_matricula: int
    fecha_matricula: date
    estado: str
    detalles: list[MatriculaDetalle] = []


class Mensaje(BaseModel):
    mensaje: str


class LoginRequest(BaseModel):
    nombre_usuario: str = Field(min_length=1, max_length=60)
    clave: str = Field(min_length=1, max_length=128)


class UsuarioSesion(BaseModel):
    id_usuario: int
    nombre_usuario: str
    nombre_mostrar: str
    cod_estudiante: Optional[str] = None
    perfil_activo: str
    perfiles: list[str]
    nombres_perfiles: dict[str, str]
    permisos: list[str]


class LoginResponse(BaseModel):
    token: str
    usuario: UsuarioSesion


class CambioPerfil(BaseModel):
    perfil: str

    @field_validator("perfil")
    @classmethod
    def normalizar_perfil(cls, valor: str) -> str:
        valor = valor.strip().upper()
        if not valor:
            raise ValueError("El perfil indicado no es válido.")
        return valor


class UsuarioCreate(BaseModel):
    nombre_usuario: str = Field(min_length=3, max_length=60)
    clave: str = Field(min_length=6, max_length=128)
    nombre_mostrar: str = Field(min_length=3, max_length=160)
    cod_estudiante: Optional[str] = Field(default=None, pattern=r"^\d{10}$")
    perfiles: list[str] = Field(min_length=1)
    activo: bool = True


class UsuarioUpdate(BaseModel):
    nombre_mostrar: str = Field(min_length=3, max_length=160)
    cod_estudiante: Optional[str] = Field(default=None, pattern=r"^\d{10}$")
    perfiles: list[str] = Field(min_length=1)
    activo: bool = True
    clave: Optional[str] = Field(default=None, min_length=6, max_length=128)


class UsuarioAdministracion(BaseModel):
    id_usuario: int
    nombre_usuario: str
    nombre_mostrar: str
    cod_estudiante: Optional[str] = None
    perfiles: list[str]
    activo: bool


class PerfilAdministracion(BaseModel):
    id_perfil: int
    codigo: str
    nombre: str
    permisos: list[str]
    total_usuarios: int


class PerfilUpdate(BaseModel):
    nombre: str = Field(min_length=3, max_length=50)
    permisos: list[str]

    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, valor: str) -> str:
        return valor.strip()


class PerfilCreate(PerfilUpdate):
    codigo: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,19}$")

    @field_validator("codigo")
    @classmethod
    def normalizar_codigo(cls, valor: str) -> str:
        return valor.strip().upper()
