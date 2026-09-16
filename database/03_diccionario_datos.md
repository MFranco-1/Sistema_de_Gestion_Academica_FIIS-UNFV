# Diccionario de datos

El modelo conserva exactamente diez tablas. No existe `plan_semestre`: los semestres disponibles se obtienen con `SELECT DISTINCT curso.semestre` para cada malla.

| Tabla | Propósito | Clave primaria | Reglas principales |
|---|---|---|---|
| `facultad` | Catálogo de facultades. | `cod_fac` | Denominación única. |
| `escuela` | Escuelas de una facultad. | `cod_fac, cod_esc` | Nombre único dentro de la facultad. |
| `docente` | Plana docente por escuela. | `cod_fac, cod_esc, cod_docente` | Docente asociado a una escuela existente. |
| `plan_estudio` | Mallas curriculares históricas y vigentes. | `cod_fac, cod_esc, corr_pe` | Año único por escuela; fechas consistentes. |
| `curso` | Cursos de cada malla. | `cod_fac, cod_esc, corr_pe, cod_curso` | Código no repetido en la malla; semestre 1–10; créditos positivos; horas no negativas; tipo obligatorio o electivo. |
| `curso_prerequisito` | Relación de prerrequisitos dentro de una malla. | `cod_fac, cod_esc, corr_pe, cod_curso, cod_curso_prerequisito` | No admite autorreferencia; ambas referencias pertenecen a la misma malla. La API exige que el requisito sea de un semestre anterior. |
| `periodo_academico` | Períodos lectivos. | `cod_periodo` | La fecha final es posterior a la inicial. |
| `horario_cabecera` | Horario de una malla en un período. | `id_horario` | Una cabecera por período y malla. |
| `horario_detalle` | Semestres habilitados en una cabecera. | `id_horario, semestre_corr` | Semestre 1–10. |
| `horario_curso` | Sesiones de cursos. | `id_horario, semestre_corr, cod_curso, cod_seccion, tipo_sesion, dia_semana, hora_inicio` | Curso de la misma malla; hora final posterior; tipos T/P; días válidos. La API rechaza cruces de aula y sección. |

## Integridad transaccional

Las operaciones de mantenimiento confirman la transacción solamente después de validar todas las reglas. Ante una violación de integridad, la API ejecuta `ROLLBACK` y devuelve un mensaje HTTP 409 o 422 comprensible. La eliminación de un curso se bloquea si es prerrequisito de otro curso o si aparece en `horario_curso`.

## Índices de apoyo

- `ix_curso_plan_semestre`: acelera los filtros encadenados.
- `ix_prerequisito_requerido`: acelera el detalle de cursos dependientes y la validación de eliminación.
- `ix_horario_aula_cruce`: apoya la detección de cruces de aula.
- `ix_horario_seccion_cruce`: apoya la detección de cruces de sección.
