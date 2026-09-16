-- 1. Semestres disponibles para una malla (GET /semestres/).
SELECT DISTINCT c.semestre
FROM curso AS c
WHERE c.cod_fac = 1 AND c.cod_esc = 1 AND c.corr_pe = 2
ORDER BY c.semestre;

-- 2. Detalle de un curso y su malla.
SELECT c.cod_curso, c.den_curso, p.den_plan, p.anio_plan, c.semestre,
       c.cred, c.ht, c.hp, c.tipo_curso
FROM curso AS c
JOIN plan_estudio AS p
  ON p.cod_fac = c.cod_fac AND p.cod_esc = c.cod_esc AND p.corr_pe = c.corr_pe
WHERE c.cod_fac = 1 AND c.cod_esc = 1
  AND c.corr_pe = 2 AND c.cod_curso = 'P19-41';

-- 3. Prerrequisitos del curso.
SELECT r.cod_curso, r.den_curso, r.semestre
FROM curso_prerequisito AS cp
JOIN curso AS r
  ON r.cod_fac = cp.cod_fac AND r.cod_esc = cp.cod_esc
 AND r.corr_pe = cp.corr_pe AND r.cod_curso = cp.cod_curso_prerequisito
WHERE cp.cod_fac = 1 AND cp.cod_esc = 1
  AND cp.corr_pe = 2 AND cp.cod_curso = 'P19-41';

-- 4. Cursos que dependen del curso seleccionado.
SELECT d.cod_curso, d.den_curso, d.semestre
FROM curso_prerequisito AS cp
JOIN curso AS d
  ON d.cod_fac = cp.cod_fac AND d.cod_esc = cp.cod_esc
 AND d.corr_pe = cp.corr_pe AND d.cod_curso = cp.cod_curso
WHERE cp.cod_fac = 1 AND cp.cod_esc = 1
  AND cp.corr_pe = 2 AND cp.cod_curso_prerequisito = 'P19-41';

-- 5. Resumen institucional por semestre (GET /resumen-semestre/).
WITH cursos_con_requisito AS (
    SELECT DISTINCT cod_fac, cod_esc, corr_pe, cod_curso
    FROM curso_prerequisito
)
SELECT COUNT(*) AS total_cursos,
       COALESCE(SUM(c.cred), 0) AS total_creditos,
       COALESCE(SUM(c.ht), 0) AS horas_teoricas,
       COALESCE(SUM(c.hp), 0) AS horas_practicas,
       COUNT(*) FILTER (WHERE c.tipo_curso = 'OBLIGATORIO') AS cursos_obligatorios,
       COUNT(*) FILTER (WHERE c.tipo_curso = 'ELECTIVO') AS cursos_electivos,
       COUNT(*) FILTER (WHERE cr.cod_curso IS NOT NULL) AS cursos_con_prerrequisitos,
       COUNT(*) FILTER (WHERE cr.cod_curso IS NULL) AS cursos_sin_prerrequisitos
FROM curso AS c
LEFT JOIN cursos_con_requisito AS cr
  ON cr.cod_fac = c.cod_fac AND cr.cod_esc = c.cod_esc
 AND cr.corr_pe = c.corr_pe AND cr.cod_curso = c.cod_curso
WHERE c.cod_fac = 1 AND c.cod_esc = 1
  AND c.corr_pe = 2 AND c.semestre = 6;

-- 6. Validación previa de cruce de aula.
SELECT hc.*
FROM horario_curso AS hc
JOIN horario_cabecera AS h ON h.id_horario = hc.id_horario
WHERE h.cod_periodo = '2026-II'
  AND hc.dia_semana = 'MARTES' AND hc.aula = 'A-204'
  AND hc.hora_inicio < TIME '15:00' AND hc.hora_fin > TIME '13:30';

-- 7. Validación previa de cruce de sección.
SELECT hc.*
FROM horario_curso AS hc
WHERE hc.id_horario = 1 AND hc.semestre_corr = 6
  AND hc.cod_seccion = 'A' AND hc.dia_semana = 'MARTES'
  AND hc.hora_inicio < TIME '15:00' AND hc.hora_fin > TIME '13:30';

-- 8. Dependencias que impiden eliminar un curso.
SELECT
  EXISTS (SELECT 1 FROM curso_prerequisito cp
          WHERE cp.cod_fac = 1 AND cp.cod_esc = 1 AND cp.corr_pe = 2
            AND cp.cod_curso_prerequisito = 'P19-41') AS tiene_dependientes,
  EXISTS (SELECT 1 FROM horario_curso hc
          WHERE hc.cod_fac = 1 AND hc.cod_esc = 1 AND hc.corr_pe = 2
            AND hc.cod_curso = 'P19-41') AS tiene_horarios;

-- 9. Historial académico de un estudiante.
SELECT m.cod_periodo, c.cod_curso, c.den_curso, md.nota_final, md.resultado
FROM matricula AS m
JOIN matricula_detalle AS md ON md.id_matricula = m.id_matricula
JOIN oferta_curso AS o ON o.id_oferta = md.id_oferta
JOIN curso AS c
  ON c.cod_fac = o.cod_fac AND c.cod_esc = o.cod_esc
 AND c.corr_pe = o.corr_pe AND c.cod_curso = o.cod_curso
WHERE m.cod_estudiante = '2021000001'
ORDER BY m.cod_periodo, c.semestre;

-- 10. Ofertas de la malla del estudiante en un período.
-- La API completa esta consulta excluyendo cursos aprobados y verificando prerrequisitos y vacantes.
SELECT o.id_oferta, o.cod_periodo, c.cod_curso, c.den_curso,
       c.semestre, o.cod_seccion, o.vacantes
FROM estudiante AS e
JOIN oferta_curso AS o
  ON o.cod_fac = e.cod_fac AND o.cod_esc = e.cod_esc AND o.corr_pe = e.corr_pe
JOIN curso AS c
  ON c.cod_fac = o.cod_fac AND c.cod_esc = o.cod_esc
 AND c.corr_pe = o.corr_pe AND c.cod_curso = o.cod_curso
WHERE e.cod_estudiante = '2021000001'
  AND o.cod_periodo = '2026-V' AND o.activo = TRUE
ORDER BY c.semestre, c.cod_curso;

-- 11. Usuarios y perfiles asignados.
SELECT u.nombre_usuario, u.nombre_mostrar, u.cod_estudiante, u.activo,
       STRING_AGG(p.nombre, ', ' ORDER BY p.nombre) AS perfiles
FROM usuario AS u
JOIN usuario_perfil AS up ON up.id_usuario = u.id_usuario
JOIN perfil AS p ON p.id_perfil = up.id_perfil
GROUP BY u.id_usuario
ORDER BY u.nombre_mostrar;
