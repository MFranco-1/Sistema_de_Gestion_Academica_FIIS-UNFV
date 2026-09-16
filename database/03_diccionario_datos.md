# Diccionario de datos

El modelo contiene diecisiete tablas. No existe `plan_semestre`: los semestres disponibles se obtienen con `SELECT DISTINCT curso.semestre` para cada malla.

| Tabla | Propósito | Clave primaria | Reglas principales |
|---|---|---|---|
| `facultad` | Catálogo de facultades. | `cod_fac` | Denominación única. |
| `escuela` | Escuelas de una facultad. | `cod_fac, cod_esc` | Nombre único dentro de la facultad. |
| `docente` | Plana docente por escuela. | `cod_fac, cod_esc, cod_docente` | Docente asociado a una escuela existente. |
| `plan_estudio` | Mallas curriculares históricas y vigentes. | `cod_fac, cod_esc, corr_pe` | Año único por escuela; fechas consistentes. |
| `curso` | Cursos de cada malla. | `cod_fac, cod_esc, corr_pe, cod_curso` | Código no repetido en la malla; semestre 1–10; créditos positivos; horas no negativas; tipo obligatorio o electivo. |
| `curso_prerequisito` | Relación de prerrequisitos dentro de una malla. | `cod_fac, cod_esc, corr_pe, cod_curso, cod_curso_prerequisito` | No admite autorreferencia; ambas referencias pertenecen a la misma malla. La API exige que el requisito sea de un semestre anterior. |
| `periodo_academico` | Períodos lectivos por año. | `cod_periodo` | Año 2000–2100; tipo I, II o VERANO; fechas consistentes. |
| `horario_cabecera` | Horario de una malla en un período. | `id_horario` | Una cabecera por período y malla. |
| `horario_detalle` | Semestres habilitados en una cabecera. | `id_horario, semestre_corr` | Semestre 1–10. |
| `horario_curso` | Sesiones de cursos. | `id_horario, semestre_corr, cod_curso, cod_seccion, tipo_sesion, dia_semana, hora_inicio` | Curso de la misma malla; hora final posterior; tipos T/P; días válidos. La API rechaza cruces de aula y sección. |
| `estudiante` | Datos del estudiante y su situación curricular. | `cod_estudiante` | DNI y correo únicos; malla existente; ciclo 1–10; estado válido. |
| `oferta_curso` | Cursos abiertos por período, malla y sección. | `id_oferta` | Una sección no se repite en el mismo período; vacantes positivas. |
| `matricula` | Cabecera de matrícula por estudiante y período. | `id_matricula` | Una matrícula por estudiante y período; conserva la malla y ciclo utilizados. |
| `matricula_detalle` | Cursos y resultados de una matrícula. | `id_matricula, id_oferta` | Nota 0–20; resultado matriculado, aprobado, desaprobado o retirado. |
| `perfil` | Catálogo de perfiles de acceso. | `id_perfil` | Código y nombre únicos; incluye Administrador y Estudiante. |
| `usuario` | Credenciales y vínculo opcional con un estudiante. | `id_usuario` | Nombre de usuario único, contraseña con hash y un estudiante por cuenta. |
| `usuario_perfil` | Perfiles asignados a cada usuario. | `id_usuario, id_perfil` | Permite que una cuenta tenga uno o varios perfiles. |

## Integridad transaccional

Las operaciones de mantenimiento confirman la transacción solamente después de validar todas las reglas. Ante una violación de integridad, la API ejecuta `ROLLBACK` y devuelve un mensaje HTTP 409 o 422 comprensible. La matrícula exige que la oferta pertenezca a la malla, esté abierta en el período, tenga vacantes y que todos los prerrequisitos estén aprobados. Un curso aprobado no puede volver a matricularse. Las contraseñas no se almacenan en texto: se derivan con PBKDF2-SHA256 y sal aleatoria.

## Índices de apoyo

- `ix_curso_plan_semestre`: acelera los filtros encadenados.
- `ix_prerequisito_requerido`: acelera el detalle de cursos dependientes y la validación de eliminación.
- `ix_horario_aula_cruce`: apoya la detección de cruces de aula.
- `ix_horario_seccion_cruce`: apoya la detección de cruces de sección.
- `ix_oferta_periodo_plan`: acelera la búsqueda de cursos abiertos por período y malla.
- `ix_matricula_estudiante`: acelera el historial y la validación de matrícula única.
