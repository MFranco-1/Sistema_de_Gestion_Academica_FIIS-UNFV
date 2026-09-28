# Diccionario de datos

El modelo contiene veintitrés tablas. No existe `plan_semestre`: los semestres disponibles se obtienen con `SELECT DISTINCT curso.semestre` para cada malla.

| Tabla | Propósito | Clave primaria | Reglas principales |
|---|---|---|---|
| `facultad` | Catálogo de facultades. | `cod_fac` | Denominación única. |
| `escuela` | Escuelas de una facultad. | `cod_fac, cod_esc` | Nombre único dentro de la facultad. |
| `docente` | Plana docente por escuela. | `cod_fac, cod_esc, cod_docente` | Docente asociado a una escuela existente; código y nombre no repetidos dentro de la escuela. No se elimina si conserva cursos asignados. |
| `plan_estudio` | Mallas curriculares históricas y vigentes. | `cod_fac, cod_esc, corr_pe` | Año único por escuela; fechas consistentes. |
| `curso` | Cursos de cada malla. | `cod_fac, cod_esc, corr_pe, cod_curso` | Código no repetido en la malla; semestre 1–10; créditos positivos; horas no negativas; tipo obligatorio o electivo. |
| `curso_prerequisito` | Relación de prerrequisitos dentro de una malla. | `cod_fac, cod_esc, corr_pe, cod_curso, cod_curso_prerequisito` | No admite autorreferencia; ambas referencias pertenecen a la misma malla. La API exige que el requisito sea de un semestre anterior. |
| `periodo_academico` | Períodos lectivos por año. | `cod_periodo` | Año 2000–2100; tipo I, II o VERANO; fechas consistentes. |
| `periodo_matricula_acceso` | Fase de matrícula por período, malla y ciclo. | `cod_periodo, cod_fac, cod_esc, corr_pe, ciclo` | Fase cerrada, tercio superior o todos; ciclo 1–10. |
| `horario_cabecera` | Horario de una malla en un período. | `id_horario` | Una cabecera por período y malla. |
| `horario_detalle` | Semestres habilitados en una cabecera. | `id_horario, semestre_corr` | Semestre 1–10. |
| `horario_curso` | Sesiones de cursos. | `id_horario, semestre_corr, cod_curso, cod_seccion, tipo_sesion, dia_semana, hora_inicio` | Curso de la misma malla; hora final posterior; tipos T/P; días válidos. La API usa bloques de 50 minutos, limita las horas T/P a la malla, aplica el turno del ciclo y rechaza cruces de aula y sección. |
| `estudiante` | Datos del estudiante y su situación curricular. | `cod_estudiante` | Código institucional obligatorio de exactamente 10 dígitos; DNI y correo únicos; malla existente; ciclo 1–10 y estado válido. |
| `oferta_curso` | Cursos abiertos por período, malla y sección. | `id_oferta` | Una sección no se repite en el mismo período; vacantes positivas; el docente opcional debe existir en la misma escuela y usa `VARCHAR(12)`. Los períodos regulares se preparan con A/B/C; en verano cada oferta se activa expresamente según demanda. |
| `prematricula` | Cabecera de la guía de prematrícula del estudiante. | `id_prematricula` | Una por estudiante; referencia un período válido. |
| `prematricula_detalle` | Ofertas elegidas en una prematrícula. | `id_prematricula, id_oferta` | No repite ofertas y elimina sus filas junto con la cabecera. |
| `matricula` | Cabecera de matrícula por estudiante y período. | `id_matricula` | Una matrícula por estudiante y período; conserva la malla y ciclo utilizados. |
| `matricula_detalle` | Cursos, notas y resultados de una matrícula. | `id_matricula, id_oferta` | Prácticas 40 %, parcial 30 % y examen final 30 %, todas de 0 a 20; `nota_final` es el promedio calculado. Resultado matriculado, aprobado, desaprobado o retirado. |
| `constancia_matricula` | Firma del estudiante y PDF oficial emitido para una matrícula. | `id_matricula` | Una constancia por matrícula; acceso exclusivo del titular o gestión académica; eliminación en cascada. |
| `permiso` | Catálogo atómico de permisos del sistema. | `codigo` | Código único usado por la autorización del backend. |
| `perfil` | Catálogo de perfiles de acceso. | `id_perfil` | Código y nombre únicos; incluye Administrador, Estudiante, Jefe de departamento, Director de escuela y Administración. |
| `perfil_permiso` | Permisos asignados a cada perfil. | `id_perfil, cod_permiso` | Relación muchos a muchos sin listas separadas por comas. |
| `usuario` | Credenciales y vínculo opcional con un estudiante. | `id_usuario` | Nombre de usuario único, contraseña con hash; las cuentas vinculadas a estudiantes usan obligatoriamente el DNI como contraseña inicial. |
| `usuario_perfil` | Perfiles asignados a cada usuario. | `id_usuario, id_perfil` | Permite que una cuenta tenga uno o varios perfiles. |

## Integridad transaccional

Las operaciones de mantenimiento confirman la transacción solamente después de validar todas las reglas. Ante una violación de integridad, la API ejecuta `ROLLBACK` y devuelve un mensaje HTTP 409 o 422 comprensible. La matrícula exige que la oferta pertenezca a la malla, esté abierta en el período, tenga vacantes, que todos los prerrequisitos estén aprobados y que la fase autorice al estudiante. Un curso aprobado no puede volver a matricularse. La tercera desaprobación del mismo curso suspende los dos semestres regulares siguientes, incluyendo los veranos intermedios. El tercio superior corresponde al 33.3 % (redondeado hacia arriba) del orden por promedio ponderado del último período cerrado y se calcula únicamente entre estudiantes de la misma base de ingreso; la prematrícula no depende de la fase. Las contraseñas no se almacenan en texto: se derivan con PBKDF2-SHA256 y sal aleatoria.

## Regla de avance de ciclo

El ciclo solo avanza al cerrar completamente una matrícula de período regular. No avanza por registrar la primera nota ni por aprobar un único curso: deben existir al menos dos cursos aprobados y los créditos aprobados deben representar como mínimo el 50 % de los créditos evaluados, excluyendo retiros. Los períodos de verano no cambian el ciclo. El avance máximo es de un ciclo y nunca supera el ciclo X.

## Índices de apoyo

- `ix_curso_plan_semestre`: acelera los filtros encadenados.
- `ix_prerequisito_requerido`: acelera el detalle de cursos dependientes y la validación de eliminación.
- `ix_horario_aula_cruce`: apoya la detección de cruces de aula.
- `ix_horario_seccion_cruce`: apoya la detección de cruces de sección.
- `ix_oferta_periodo_plan`: acelera la búsqueda de cursos abiertos por período y malla.
- `ix_oferta_docente`: acelera la asignación y validación de docentes por escuela.
- `ix_prematricula_detalle_oferta`: apoya la integridad y búsqueda de ofertas guardadas como guía.
- `ix_perfil_permiso_codigo`: acelera la consulta inversa de perfiles por permiso.
- `ix_matricula_estudiante`: acelera el historial y la validación de matrícula única.
