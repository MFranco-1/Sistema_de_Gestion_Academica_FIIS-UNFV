from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, ForeignKey, ForeignKeyConstraint,
    Integer, String, Time, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Facultad(Base):
    __tablename__ = "facultad"
    cod_fac = Column(Integer, primary_key=True)
    den_fac = Column(String(120), nullable=False, unique=True)
    escuelas = relationship("Escuela", back_populates="facultad")


class Escuela(Base):
    __tablename__ = "escuela"
    cod_fac = Column(Integer, ForeignKey("facultad.cod_fac"), primary_key=True)
    cod_esc = Column(Integer, primary_key=True)
    den_escuela = Column(String(120), nullable=False)
    __table_args__ = (
        UniqueConstraint("cod_fac", "den_escuela", name="uq_escuela_nombre_facultad"),
    )
    facultad = relationship("Facultad", back_populates="escuelas")
    planes_estudio = relationship("PlanEstudio", back_populates="escuela")
    docentes = relationship("Docente", back_populates="escuela")


class Docente(Base):
    __tablename__ = "docente"
    cod_fac = Column(Integer, primary_key=True)
    cod_esc = Column(Integer, primary_key=True)
    cod_docente = Column(String(12), primary_key=True)
    apellidos_nombres = Column(String(160), nullable=False)
    categoria = Column(String(30), nullable=False)
    dedicacion = Column(String(30), nullable=False)
    departamento = Column(String(100), nullable=False)
    fuente = Column(String(120), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["cod_fac", "cod_esc"], ["escuela.cod_fac", "escuela.cod_esc"],
            name="fk_docente_escuela",
        ),
        UniqueConstraint("cod_fac", "cod_esc", "apellidos_nombres", name="uq_docente_nombre_escuela"),
    )
    escuela = relationship("Escuela", back_populates="docentes")


class PlanEstudio(Base):
    __tablename__ = "plan_estudio"
    cod_fac = Column(Integer, primary_key=True)
    cod_esc = Column(Integer, primary_key=True)
    corr_pe = Column(Integer, primary_key=True)
    den_plan = Column(String(120), nullable=False)
    anio_plan = Column(Integer, nullable=False)
    fecha_vigencia = Column(Date, nullable=False)
    fecha_baja = Column(Date, nullable=True)
    vigente = Column(Boolean, nullable=False, default=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["cod_fac", "cod_esc"], ["escuela.cod_fac", "escuela.cod_esc"],
            name="fk_plan_escuela",
        ),
        UniqueConstraint("cod_fac", "cod_esc", "anio_plan", name="uq_plan_anio_escuela"),
        CheckConstraint("anio_plan BETWEEN 1900 AND 2100", name="ck_plan_anio"),
        CheckConstraint("fecha_baja IS NULL OR fecha_baja >= fecha_vigencia", name="ck_plan_fechas"),
    )
    escuela = relationship("Escuela", back_populates="planes_estudio")
    cursos = relationship("Curso", back_populates="plan_estudio")


class Curso(Base):
    __tablename__ = "curso"
    cod_fac = Column(Integer, primary_key=True)
    cod_esc = Column(Integer, primary_key=True)
    corr_pe = Column(Integer, primary_key=True)
    cod_curso = Column(String(20), primary_key=True)
    den_curso = Column(String(160), nullable=False)
    semestre = Column(Integer, nullable=False)
    ht = Column(Integer, nullable=False, default=0)
    hp = Column(Integer, nullable=False, default=0)
    cred = Column(Integer, nullable=False)
    tipo_curso = Column(String(20), nullable=False, default="OBLIGATORIO")
    __table_args__ = (
        ForeignKeyConstraint(
            ["cod_fac", "cod_esc", "corr_pe"],
            ["plan_estudio.cod_fac", "plan_estudio.cod_esc", "plan_estudio.corr_pe"],
            name="fk_curso_plan",
        ),
        CheckConstraint("semestre BETWEEN 1 AND 10", name="ck_curso_semestre"),
        CheckConstraint("ht >= 0 AND hp >= 0", name="ck_curso_horas"),
        CheckConstraint("cred > 0", name="ck_curso_creditos"),
        CheckConstraint("tipo_curso IN ('OBLIGATORIO', 'ELECTIVO')", name="ck_curso_tipo"),
    )
    plan_estudio = relationship("PlanEstudio", back_populates="cursos")


class CursoPrerequisito(Base):
    __tablename__ = "curso_prerequisito"
    cod_fac = Column(Integer, primary_key=True)
    cod_esc = Column(Integer, primary_key=True)
    corr_pe = Column(Integer, primary_key=True)
    cod_curso = Column(String(20), primary_key=True)
    cod_curso_prerequisito = Column(String(20), primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["cod_fac", "cod_esc", "corr_pe", "cod_curso"],
            ["curso.cod_fac", "curso.cod_esc", "curso.corr_pe", "curso.cod_curso"],
            name="fk_prerequisito_curso", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["cod_fac", "cod_esc", "corr_pe", "cod_curso_prerequisito"],
            ["curso.cod_fac", "curso.cod_esc", "curso.corr_pe", "curso.cod_curso"],
            name="fk_prerequisito_requerido", ondelete="RESTRICT",
        ),
        CheckConstraint("cod_curso <> cod_curso_prerequisito", name="ck_prerequisito_distinto"),
    )


class PeriodoAcademico(Base):
    __tablename__ = "periodo_academico"
    cod_periodo = Column(String(10), primary_key=True)
    den_periodo = Column(String(80), nullable=False, unique=True)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    __table_args__ = (CheckConstraint("fecha_fin > fecha_inicio", name="ck_periodo_fechas"),)


class HorarioCabecera(Base):
    __tablename__ = "horario_cabecera"
    id_horario = Column(Integer, primary_key=True, autoincrement=True)
    cod_periodo = Column(String(10), ForeignKey("periodo_academico.cod_periodo"), nullable=False)
    cod_fac = Column(Integer, nullable=False)
    cod_esc = Column(Integer, nullable=False)
    corr_pe = Column(Integer, nullable=False)
    fecha_creacion = Column(Date, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["cod_fac", "cod_esc", "corr_pe"],
            ["plan_estudio.cod_fac", "plan_estudio.cod_esc", "plan_estudio.corr_pe"],
            name="fk_horario_plan",
        ),
        UniqueConstraint("id_horario", "cod_fac", "cod_esc", "corr_pe", name="uq_horario_id_plan"),
        UniqueConstraint("cod_periodo", "cod_fac", "cod_esc", "corr_pe", name="uq_horario_periodo_plan"),
    )


class HorarioDetalle(Base):
    __tablename__ = "horario_detalle"
    id_horario = Column(Integer, ForeignKey("horario_cabecera.id_horario", ondelete="CASCADE"), primary_key=True)
    semestre_corr = Column(Integer, primary_key=True)
    semestre_desc = Column(String(30), nullable=False)
    __table_args__ = (CheckConstraint("semestre_corr BETWEEN 1 AND 10", name="ck_horario_semestre"),)


class HorarioCurso(Base):
    __tablename__ = "horario_curso"
    id_horario = Column(Integer, primary_key=True)
    semestre_corr = Column(Integer, primary_key=True)
    cod_curso = Column(String(20), primary_key=True)
    cod_seccion = Column(String(10), primary_key=True)
    tipo_sesion = Column(String(1), primary_key=True)
    cod_fac = Column(Integer, nullable=False)
    cod_esc = Column(Integer, nullable=False)
    corr_pe = Column(Integer, nullable=False)
    dia_semana = Column(String(10), primary_key=True)
    hora_inicio = Column(Time, primary_key=True)
    hora_fin = Column(Time, nullable=False)
    aula = Column(String(30), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["id_horario", "semestre_corr"],
            ["horario_detalle.id_horario", "horario_detalle.semestre_corr"],
            name="fk_horario_curso_detalle", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["id_horario", "cod_fac", "cod_esc", "corr_pe"],
            [
                "horario_cabecera.id_horario", "horario_cabecera.cod_fac",
                "horario_cabecera.cod_esc", "horario_cabecera.corr_pe",
            ],
            name="fk_horario_curso_plan_cabecera", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["cod_fac", "cod_esc", "corr_pe", "cod_curso"],
            ["curso.cod_fac", "curso.cod_esc", "curso.corr_pe", "curso.cod_curso"],
            name="fk_horario_curso_malla",
        ),
        CheckConstraint("tipo_sesion IN ('T', 'P')", name="ck_horario_tipo_sesion"),
        CheckConstraint("dia_semana IN ('LUNES','MARTES','MIERCOLES','JUEVES','VIERNES','SABADO')", name="ck_horario_dia"),
        CheckConstraint("hora_fin > hora_inicio", name="ck_horario_horas"),
    )
