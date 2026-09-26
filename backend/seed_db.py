import argparse
from datetime import date, time

from sqlalchemy import text

from app import auth, models
from app.database import Base, SessionLocal, engine


FACULTAD = 1
ESCUELA = 1

CODIGOS_ESTUDIANTE_ANTIGUOS = {
    "20260001": "2026000001", "20250002": "2025000002",
    "20250003": "2025000003", "20240004": "2024000004",
    "20240005": "2024000005", "20230007": "2023000007",
    "20220008": "2022000008", "20210009": "2021000009",
    "20200010": "2020000010",
}


def migrar_codigos_estudiante() -> None:
    """Convierte códigos demo antiguos conservando usuarios y matrículas."""
    with engine.begin() as connection:
        for anterior, nuevo in CODIGOS_ESTUDIANTE_ANTIGUOS.items():
            fila = connection.execute(text(
                "SELECT dni, correo FROM estudiante WHERE cod_estudiante = :codigo"
            ), {"codigo": anterior}).mappings().first()
            if not fila:
                continue
            if connection.execute(text(
                "SELECT 1 FROM estudiante WHERE cod_estudiante = :codigo"
            ), {"codigo": nuevo}).first():
                raise RuntimeError(f"Ya existe el código destino {nuevo}; no se modificó {anterior}.")
            correo_nuevo = f"{nuevo}@unfv.edu.pe" if fila["correo"] == f"{anterior}@unfv.edu.pe" else fila["correo"]
            connection.execute(text(
                "UPDATE estudiante SET dni = :dni_tmp, correo = :correo_tmp WHERE cod_estudiante = :anterior"
            ), {"dni_tmp": "8" + fila["dni"][1:], "correo_tmp": f"{anterior}@migracion.invalid", "anterior": anterior})
            connection.execute(text("""
                INSERT INTO estudiante
                    (cod_estudiante, dni, apellidos_nombres, correo, cod_fac, cod_esc, corr_pe, ciclo_actual, estado)
                SELECT :nuevo, :dni, apellidos_nombres, :correo, cod_fac, cod_esc, corr_pe, ciclo_actual, estado
                FROM estudiante WHERE cod_estudiante = :anterior
            """), {"nuevo": nuevo, "dni": fila["dni"], "correo": correo_nuevo, "anterior": anterior})
            connection.execute(text(
                "UPDATE matricula SET cod_estudiante = :nuevo WHERE cod_estudiante = :anterior"
            ), {"nuevo": nuevo, "anterior": anterior})
            connection.execute(text("""
                UPDATE usuario SET cod_estudiante = :nuevo,
                    nombre_usuario = CASE WHEN nombre_usuario = :anterior THEN :nuevo ELSE nombre_usuario END
                WHERE cod_estudiante = :anterior
            """), {"nuevo": nuevo, "anterior": anterior})
            connection.execute(text(
                "DELETE FROM estudiante WHERE cod_estudiante = :anterior"
            ), {"anterior": anterior})


def migrar_periodos_y_ofertas() -> None:
    """Completa la estructura y datos de matrícula en bases anteriores."""
    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE periodo_academico ADD COLUMN IF NOT EXISTS anio INTEGER")
        connection.exec_driver_sql("ALTER TABLE periodo_academico ADD COLUMN IF NOT EXISTS tipo_periodo VARCHAR(10)")
        connection.exec_driver_sql(
            "ALTER TABLE periodo_academico ADD COLUMN IF NOT EXISTS matricula_accesos VARCHAR(500) NOT NULL DEFAULT ''"
        )
        connection.execute(text("""
            UPDATE periodo_academico
            SET anio = CAST(SUBSTRING(cod_periodo FROM 1 FOR 4) AS INTEGER),
                tipo_periodo = CASE
                    WHEN cod_periodo LIKE '%-II' THEN 'II'
                    WHEN cod_periodo LIKE '%-I' THEN 'I'
                    ELSE 'VERANO'
                END
            WHERE anio IS NULL OR tipo_periodo IS NULL
        """))
        connection.exec_driver_sql("ALTER TABLE periodo_academico ALTER COLUMN anio SET NOT NULL")
        connection.exec_driver_sql("ALTER TABLE periodo_academico ALTER COLUMN tipo_periodo SET NOT NULL")
        connection.execute(text("""
            INSERT INTO periodo_academico
                (cod_periodo, den_periodo, anio, tipo_periodo, fecha_inicio, fecha_fin, activo)
            VALUES
                ('2024-V','Ciclo de verano 2024',2024,'VERANO','2024-01-08','2024-02-29',FALSE),
                ('2024-I','Semestre académico 2024-I',2024,'I','2024-03-18','2024-07-20',FALSE),
                ('2024-II','Semestre académico 2024-II',2024,'II','2024-08-19','2024-12-21',FALSE),
                ('2025-V','Ciclo de verano 2025',2025,'VERANO','2025-01-06','2025-02-28',FALSE),
                ('2025-I','Semestre académico 2025-I',2025,'I','2025-03-17','2025-07-19',FALSE),
                ('2025-II','Semestre académico 2025-II',2025,'II','2025-08-18','2025-12-20',FALSE),
                ('2026-V','Ciclo de verano 2026',2026,'VERANO','2026-01-05','2026-02-28',FALSE),
                ('2026-I','Semestre académico 2026-I',2026,'I','2026-03-16','2026-07-18',FALSE),
                ('2026-II','Semestre académico 2026-II',2026,'II','2026-08-17','2026-12-19',TRUE)
            ON CONFLICT (cod_periodo) DO UPDATE
            SET anio = EXCLUDED.anio, tipo_periodo = EXCLUDED.tipo_periodo
        """))
        # Mantener siempre disponibles los dos años académicos siguientes.
        for anio in range(2027, date.today().year + 3):
            periodos_futuros = (
                (f"{anio}-V", f"Ciclo de verano {anio}", "VERANO", f"{anio}-01-05", f"{anio}-02-28"),
                (f"{anio}-I", f"Semestre académico {anio}-I", "I", f"{anio}-03-15", f"{anio}-07-20"),
                (f"{anio}-II", f"Semestre académico {anio}-II", "II", f"{anio}-08-15", f"{anio}-12-20"),
            )
            for codigo, nombre, tipo, inicio, fin in periodos_futuros:
                connection.execute(text("""
                    INSERT INTO periodo_academico
                        (cod_periodo, den_periodo, anio, tipo_periodo, fecha_inicio, fecha_fin, activo)
                    VALUES (:codigo, :nombre, :anio, :tipo, :inicio, :fin, FALSE)
                    ON CONFLICT (cod_periodo) DO NOTHING
                """), {"codigo": codigo, "nombre": nombre, "anio": anio, "tipo": tipo, "inicio": inicio, "fin": fin})
        connection.execute(text("""
            INSERT INTO oferta_curso
                (cod_periodo, cod_fac, cod_esc, corr_pe, cod_curso, cod_seccion, vacantes, activo)
            SELECT p.cod_periodo, c.cod_fac, c.cod_esc, c.corr_pe, c.cod_curso, 'A', 35, TRUE
            FROM periodo_academico p CROSS JOIN curso c
            WHERE p.tipo_periodo <> 'VERANO'
            ON CONFLICT (cod_periodo, cod_fac, cod_esc, corr_pe, cod_curso, cod_seccion)
            DO NOTHING
        """))
        marca_verano = connection.execute(text(
            "SELECT obj_description('oferta_curso'::regclass, 'pg_class')"
        )).scalar()
        if marca_verano != "verano_bajo_demanda_v1":
            connection.execute(text("""
                UPDATE oferta_curso AS oferta
                SET activo = FALSE, cod_docente = NULL
                FROM periodo_academico AS periodo
                WHERE periodo.cod_periodo = oferta.cod_periodo
                  AND periodo.tipo_periodo = 'VERANO'
                  AND NOT EXISTS (
                      SELECT 1 FROM matricula_detalle AS detalle
                      WHERE detalle.id_oferta = oferta.id_oferta
                  )
            """))
            connection.exec_driver_sql(
                "COMMENT ON TABLE oferta_curso IS 'verano_bajo_demanda_v1'"
            )


def inicializar_estudiantes_primer_ciclo() -> None:
    """Normaliza una sola vez los estudiantes actuales al primer ciclo."""
    with engine.begin() as connection:
        marca = connection.execute(text(
            "SELECT obj_description('estudiante'::regclass, 'pg_class')"
        )).scalar()
        if marca != "ciclos_inicializados_2026":
            connection.exec_driver_sql("UPDATE estudiante SET ciclo_actual = 1")
            connection.exec_driver_sql(
                "COMMENT ON TABLE estudiante IS 'ciclos_inicializados_2026'"
            )


def reparar_avance_ciclos() -> None:
    """Repara matrículas cerradas antiguas que no actualizaron el ciclo del alumno."""
    with engine.begin() as connection:
        connection.execute(text("""
            WITH avances AS (
                SELECT m.cod_estudiante,
                       LEAST(MAX(m.ciclo_matricula) + 1, 10) AS ciclo_correspondiente
                FROM matricula m
                WHERE m.estado = 'CERRADA'
                  AND EXISTS (
                      SELECT 1
                      FROM matricula_detalle md
                      WHERE md.id_matricula = m.id_matricula
                        AND md.resultado = 'APROBADO'
                  )
                GROUP BY m.cod_estudiante
            )
            UPDATE estudiante e
            SET ciclo_actual = a.ciclo_correspondiente
            FROM avances a
            WHERE e.cod_estudiante = a.cod_estudiante
              AND e.ciclo_actual < a.ciclo_correspondiente
        """))


def curso(codigo, nombre, semestre, creditos, ht=0, hp=0, tipo="OBLIGATORIO"):
    return {
        "cod_curso": str(codigo), "den_curso": nombre, "semestre": semestre,
        "ht": ht, "hp": hp, "cred": creditos, "tipo_curso": tipo,
    }


CURSOS_2010 = [
    curso("2A0125", "Lógica y algoritmos", 1, 3),
    curso("3B0058", "Álgebra lineal", 1, 2),
    curso("5A0060", "Computación e informática básica", 1, 4),
    curso("2C0187", "Lenguaje y redacción", 1, 4),
    curso("6C0037", "Metodología de la investigación", 1, 3),
    curso("8B0116", "Introducción a la Ingeniería de Sistemas", 1, 2),
    curso("3B0103", "Matemática básica", 1, 5),
    curso("3A0014", "Física", 2, 4),
    curso("7C0080", "Economía", 2, 3),
    curso("3B0165", "Cálculo diferencial e integral", 2, 5),
    curso("8B0109", "Algoritmos y estructura de datos", 2, 4),
    curso("7B0192", "Contabilidad general", 2, 3),
    curso("7A0472", "Administración de negocios", 2, 3),
    curso("8F0123", "Electromagnetismo y ondas", 3, 4),
    curso("5B0110", "Estadística y probabilidades", 3, 4),
    curso("3B0166", "Ecuaciones diferenciales", 3, 4),
    curso("8E0035", "Lenguaje de programación estructurado", 3, 4),
    curso("8B0073", "Teoría de sistemas", 3, 3),
    curso("8E0039", "Programación lineal", 3, 3),
    curso("8F0127", "Sistemas digitales", 4, 4),
    curso("5B0021", "Estadística inferencial", 4, 4),
    curso("3B0170", "Matemáticas discretas", 4, 4),
    curso("8E0036", "Lenguaje de programación orientado a objetos", 4, 4),
    curso("6C0006", "Investigación operativa", 4, 3),
    curso("7B0184", "Costos y presupuestos", 4, 3),
    curso("5A0063", "Fundamentos de base de datos", 5, 4),
    curso("8E0037", "Lenguaje de programación orientado a web", 5, 3),
    curso("8E0003", "Sistemas operativos", 5, 4),
    curso("7B0197", "Ingeniería de procesos de negocios", 5, 4),
    curso("5A0015", "Arquitectura del computador", 5, 3),
    curso("8B0110", "Análisis y diseño de sistemas de información", 5, 4),
    curso("2H0033", "Fundamentos de comunicaciones", 6, 4),
    curso("7C0081", "Ingeniería económica", 6, 3),
    curso("8B0068", "Sistemas de base de datos", 6, 4),
    curso("2A0124", "Filosofía y ética", 6, 4),
    curso("2D0109", "Sistemas de gestión del potencial humano", 6, 3),
    curso("8B0059", "Ingeniería de software I", 6, 4),
    curso("8B0111", "Arquitectura y conectividad de redes", 7, 3),
    curso("7A0480", "Marketing empresarial", 7, 3),
    curso("8B0085", "Dinámica de sistemas", 7, 3),
    curso("7A0013", "Administración financiera", 7, 3),
    curso("8B0114", "Ingeniería de software II", 7, 3),
    curso("8B0071", "Taller de base de datos", 7, 4),
    curso("2I0230", "Geopolítica y defensa nacional", 7, 3),
    curso("8B0108", "Administración de redes", 8, 4),
    curso("2I0229", "Derecho informático y empresarial", 8, 3),
    curso("8B0072", "Taller de integración de sistemas", 8, 4),
    curso("7A0482", "Planeamiento estratégico de negocios", 8, 4),
    curso("8B0067", "Simulación de sistemas", 8, 3),
    curso("8F0126", "Negocios electrónicos", 8, 4),
    curso("GA0062", "Prácticas preprofesionales I", 9, 6),
    curso("7A0477", "Liderazgo y creatividad empresarial", 9, 3),
    curso("5A0062", "Formulación y evaluación de proyectos informáticos", 9, 4),
    curso("8B0074", "Tópicos especiales en Ingeniería de Sistemas I", 9, 3),
    curso("8F0124", "Inteligencia artificial", 9, 4),
    curso("8B0118", "Seguridad en redes y sistemas de información", 9, 3),
    curso("GA0063", "Prácticas preprofesionales II", 10, 6),
    curso("HC0107", "Seminario de tesis", 10, 2),
    curso("BA0328", "Gestión del conocimiento", 10, 3),
    curso("8B0112", "Gerencia de proyectos de TI y comunicaciones", 10, 4),
    curso("8B0121", "Tópicos especiales en Ingeniería de Sistemas II", 10, 4),
    curso("8B0003", "Auditoría de sistemas", 10, 4),
]


NOMBRES_2019 = {
    1: "Inglés I", 2: "Lenguaje y comunicación", 3: "Filosofía y ética",
    4: "Fundamentos de cálculo", 5: "Metodología del trabajo universitario",
    6: "Actividades culturales y deportivas", 7: "Matemática",
    8: "Introducción a la Ingeniería de Sistemas", 9: "Inglés II",
    10: "Liderazgo y desarrollo personal", 11: "Medio ambiente y desarrollo sostenible",
    12: "Tecnologías de la información y comunicación", 13: "Sociología",
    14: "Teoría de sistemas", 15: "Cálculo diferencial e integral",
    16: "Fundamentos de programación I", 17: "Inglés III",
    18: "Psicología organizacional", 19: "Estadística",
    20: "Geopolítica y realidad nacional", 21: "Metodología de la investigación científica",
    22: "Física", 23: "Ecuaciones diferenciales", 24: "Fundamentos de programación II",
    25: "Programación aplicada I", 26: "Gestión contable", 27: "Estadística II",
    28: "Investigación operativa", 29: "Electromagnetismo y electrónica básica",
    30: "Matemáticas discretas", 31: "Programación aplicada II",
    32: "Ingeniería de costos y presupuestos", 33: "Fundamentos de bases de datos",
    34: "Ingeniería de procesos de negocios", 35: "Sistemas digitales y arquitectura de computadoras",
    36: "Sistemas operativos", 37: "Dinámica de sistemas",
    38: "Electivo I - Certificación progresiva", 39: "Programación aplicada III",
    40: "Administración financiera", 41: "Diseño de bases de datos",
    42: "Ingeniería de requerimientos", 43: "Fundamentos de redes y conectividad",
    44: "Arquitectura de software", 45: "Electivo II - Programming with SQL",
    46: "Ingeniería de software", 47: "Investigación aplicada",
    48: "Administración y gestión de bases de datos", 49: "Planeamiento de recursos empresariales",
    50: "Arquitectura y conectividad de redes", 51: "Ingeniería del conocimiento",
    52: "Simulación de sistemas", 53: "Electivo III - Certificación progresiva",
    54: "Taller de tesis I", 55: "Taller de integración de sistemas",
    56: "Tópicos especiales de Internet de las Cosas", 57: "Inteligencia de negocios",
    58: "Seguridad en redes y sistemas de información", 59: "Inteligencia artificial",
    60: "Taller de tesis II", 61: "Evaluación de proyectos de TI",
    62: "Tópicos especiales de Big Data", 63: "Arquitectura empresarial",
    64: "Ciberseguridad", 65: "Prácticas preprofesionales I",
    66: "Auditoría de sistemas de información", 67: "Gerencia de proyectos de TI",
    68: "Fundamentos de Business Analytics", 69: "Tecnologías emergentes e innovación tecnológica",
    70: "Prácticas preprofesionales II", 71: "Trabajo de investigación",
}

SEMESTRES_2019 = {
    1: range(1, 9), 2: range(9, 17), 3: range(17, 25), 4: range(25, 32),
    5: range(32, 39), 6: range(39, 46), 7: range(46, 54),
    8: range(54, 60), 9: range(60, 66), 10: range(66, 72),
}

CREDITOS_2019 = {
    1: 1, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 5, 8: 4,
    9: 1, 10: 3, 11: 3, 12: 2, 13: 2, 14: 3, 15: 5, 16: 3,
    17: 1, 18: 2, 19: 3, 20: 3, 21: 3, 22: 3, 23: 4, 24: 3,
    25: 4, 26: 3, 27: 3, 28: 3, 29: 3, 30: 3, 31: 3,
    32: 3, 33: 4, 34: 3, 35: 4, 36: 3, 37: 3, 38: 2,
    39: 3, 40: 3, 41: 4, 42: 3, 43: 4, 44: 3, 45: 2,
    46: 3, 47: 3, 48: 3, 49: 3, 50: 3, 51: 2, 52: 3, 53: 2,
    54: 3, 55: 3, 56: 4, 57: 3, 58: 3, 59: 3,
    60: 3, 61: 3, 62: 3, 63: 2, 64: 3, 65: 4,
    66: 3, 67: 4, 68: 3, 69: 3, 70: 4, 71: 3,
}


def construir_cursos_2019():
    cursos = []
    for semestre, numeros in SEMESTRES_2019.items():
        for numero in numeros:
            creditos = CREDITOS_2019[numero]
            tipo = "ELECTIVO" if numero in (38, 45, 53) else "OBLIGATORIO"
            if numero in (1, 6, 9, 17):
                ht, hp = 0, 2
            elif numero in (65, 70):
                ht, hp = 0, 8
            elif creditos >= 4:
                ht, hp = 2, 4
            else:
                ht, hp = (1, 2) if creditos == 2 else (2, 2)
            cursos.append(curso(f"P19-{numero:02d}", NOMBRES_2019[numero], semestre, creditos, ht, hp, tipo))
    return cursos


PREREQUISITOS_2010 = {
    "3A0014": ["3B0103"], "3B0165": ["3B0103"], "8B0109": ["2A0125"],
    "8F0123": ["3A0014"], "5B0110": ["3B0103"], "3B0166": ["3B0165"],
    "8E0035": ["5A0060", "8B0109"], "8B0073": ["8B0116"], "8E0039": ["3B0058"],
    "8F0127": ["8F0123"], "5B0021": ["5B0110"], "3B0170": ["3B0166"],
    "8E0036": ["8E0035"], "6C0006": ["5B0110"], "7B0184": ["7B0192", "7C0080"],
    "5A0063": ["8B0109"], "8E0037": ["8E0036"], "8E0003": ["8E0035"],
    "7B0197": ["7A0472"], "5A0015": ["8F0127"], "8B0110": ["8B0073", "8E0036"],
    "2H0033": ["5A0015"], "7C0081": ["7B0184"], "8B0068": ["5A0063"],
    "2A0124": ["2C0187"], "2D0109": ["8B0110"], "8B0059": ["8B0110"],
    "8B0111": ["2H0033"], "7A0480": ["7B0197"], "8B0085": ["3B0170"],
    "7A0013": ["7C0081"], "8B0114": ["8B0059"], "8B0071": ["8B0068"],
    "2I0230": ["2A0124"], "8B0108": ["8B0111"], "2I0229": ["7A0480"],
    "8B0072": ["8B0114"], "7A0482": ["7A0480"], "8B0067": ["8B0085"],
    "8F0126": ["7B0197"], "GA0062": ["8B0072", "8B0111"], "7A0477": ["7A0482"],
    "5A0062": ["7A0482"], "8B0074": ["8B0072"], "8F0124": ["8B0067"],
    "8B0118": ["8B0108"], "GA0063": ["GA0062"], "HC0107": ["5A0062"],
    "BA0328": ["8F0124"], "8B0112": ["7A0482", "8B0118"],
    "8B0121": ["8B0074"], "8B0003": ["8B0118"],
}

PREREQUISITOS_2019 = {
    9: [1], 10: [2], 12: [8], 13: [3], 14: [8], 15: [7], 17: [9], 18: [10],
    19: [4], 20: [11], 22: [15], 23: [15], 24: [16], 25: [24], 26: [18],
    27: [19], 28: [19], 29: [22], 30: [23], 31: [25], 32: [26], 33: [24],
    34: [28], 35: [29], 36: [30], 37: [30], 39: [31], 40: [32], 41: [33],
    42: [34], 43: [35], 44: [36], 45: [38], 46: [42], 47: [21], 48: [41],
    49: [42], 50: [43], 51: [44], 52: [37], 53: [45], 54: [47], 55: [46],
    56: [48], 57: [49], 58: [50], 59: [51], 60: [54], 61: [55], 62: [56],
    63: [57], 64: [58], 66: [64], 67: [61], 68: [56], 69: [59], 70: [65], 71: [54],
}


DOCENTES_SISTEMAS = [
    ("78153", "Acevedo Borrego, Adolfo Oswaldo", "PRINCIPAL", "TIEMPO PARCIAL"),
    ("94032", "Alcantara Ramirez, Modesto Roland", "AUXILIAR", "TIEMPO PARCIAL"),
    ("80033", "Alfaro Bardales Vda. de Ontaneda, Maria Renee", "PRINCIPAL", "TIEMPO COMPLETO"),
    ("79086", "Alfaro Bernedo, Juan Oswaldo", "PRINCIPAL", "TIEMPO COMPLETO"),
    ("82301", "Alvarado Alvarado, Jose Orlando", "ASOCIADO", "TIEMPO COMPLETO"),
    ("2020042", "Aparicio Montenegro, Pablo Roberto", "AUXILIAR", "TIEMPO COMPLETO"),
    ("74119", "Cachay Boza, Orestes", "PRINCIPAL", "TIEMPO PARCIAL"),
    ("75252", "Cano Espada, Jaime", "ASOCIADO", "TIEMPO PARCIAL"),
    ("2020043", "Carranza Barrena, Wilfredo Eduardo", "AUXILIAR", "TIEMPO COMPLETO"),
    ("2020044", "Cohello Aguirre, Rogelio Gonzalo", "AUXILIAR", "TIEMPO COMPLETO"),
    ("94101", "Franco Del Carpio, Carlos Miguel", "ASOCIADO", "TIEMPO COMPLETO"),
    ("2001038", "Gamboa Cruzado, Javier Arturo", "AUXILIAR", "TIEMPO PARCIAL"),
    ("94105", "Gavino Ramos, Martin Sabino", "ASOCIADO", "TIEMPO COMPLETO"),
    ("2020046", "Hilario Falcon, Francisco Manuel", "AUXILIAR", "TIEMPO COMPLETO"),
    ("89189", "Huapaya Sotero, Armando Ricardo", "ASOCIADO", "TIEMPO COMPLETO"),
    ("79322", "Jara Bautista, Lucio", "ASOCIADO", "TIEMPO COMPLETO"),
    ("2018139", "Leon Velarde, Cesar Gerardo", "AUXILIAR", "TIEMPO COMPLETO"),
    ("2020047", "Lezama Gonzales, Pedro Martin", "AUXILIAR", "TIEMPO COMPLETO"),
    ("2019053", "Lira Camargo, Jorge", "AUXILIAR", "TIEMPO COMPLETO"),
    ("84032", "Lopez Juarez, Bertha Beatriz", "PRINCIPAL", "TIEMPO COMPLETO"),
    ("73109", "Magallanes Villaverde, Heriberto Reginaldo", "ASOCIADO", "TIEMPO PARCIAL"),
    ("88113", "Mayhuasca Guerra, Jorge Victor", "PRINCIPAL", "TIEMPO COMPLETO"),
    ("79090", "Michue Salguedo, Efren Silverio", "PRINCIPAL", "TIEMPO PARCIAL"),
    ("79300", "Mujica Ruiz, Oscar Hugo", "PRINCIPAL", "TIEMPO COMPLETO"),
    ("78112", "Muñoz Ramos, Luis Avelino", "ASOCIADO", "TIEMPO PARCIAL"),
    ("2021056", "Narro Andrade, Manuel Guillermo", "AUXILIAR", "TIEMPO COMPLETO"),
    ("2020105", "Ogosi Auqui, Jose Antonio", "AUXILIAR", "TIEMPO COMPLETO"),
    ("2012090", "Petrlik Azabache, Ivan Carlo", "AUXILIAR", "TIEMPO COMPLETO"),
    ("82154", "Ramirez Saavedra, Luz Noemi", "ASOCIADO", "TIEMPO COMPLETO"),
    ("75105", "Rojas Carretero, Henry", "PRINCIPAL", "TIEMPO PARCIAL"),
    ("2020108", "Rojas Romero, Karin Corina", "AUXILIAR", "TIEMPO COMPLETO"),
    ("2011197", "Salazar Deza, Carmen Angelica", "AUXILIAR", "TIEMPO COMPLETO"),
    ("2020048", "Sotelo Antaurco, Santos Ciriaco", "AUXILIAR", "TIEMPO COMPLETO"),
    ("2001039", "Soto Soto, Luis", "AUXILIAR", "TIEMPO PARCIAL"),
    ("2019054", "Sotomayor Abarca, Julio Elmer", "AUXILIAR", "TIEMPO COMPLETO"),
    ("86317", "Vales Carrillo, Jorge Alberto", "ASOCIADO", "TIEMPO COMPLETO"),
    ("2013087", "Vera Tito, Francisca Sonia", "AUXILIAR", "TIEMPO COMPLETO"),
    ("2013088", "Yucra Sotomayor, Daniel Alejandro", "AUXILIAR", "TIEMPO COMPLETO"),
]


def insertar_docentes(db):
    for codigo, nombre, categoria, dedicacion in DOCENTES_SISTEMAS:
        db.add(models.Docente(
            cod_fac=FACULTAD,
            cod_esc=ESCUELA,
            cod_docente=codigo,
            apellidos_nombres=nombre,
            categoria=categoria,
            dedicacion=dedicacion,
            departamento="Departamento Académico de Ingeniería de Sistemas",
            fuente="Portal institucional FIIS-UNFV",
        ))


def insertar_plan(db, corr_pe, plan, cursos, prerequisitos):
    db.add(models.PlanEstudio(**plan))
    for item in cursos:
        db.add(models.Curso(cod_fac=FACULTAD, cod_esc=ESCUELA, corr_pe=corr_pe, **item))
    db.flush()
    for codigo, requisitos in prerequisitos.items():
        cod_curso = f"P19-{codigo:02d}" if isinstance(codigo, int) else codigo
        for requisito in requisitos:
            cod_requisito = f"P19-{requisito:02d}" if isinstance(requisito, int) else requisito
            db.add(models.CursoPrerequisito(
                cod_fac=FACULTAD, cod_esc=ESCUELA, corr_pe=corr_pe,
                cod_curso=cod_curso, cod_curso_prerequisito=cod_requisito,
            ))


def asegurar_horarios_y_secciones(db):
    """Abre A/B/C y programa el período regular activo y el siguiente."""
    if not db.query(models.PlanEstudio).filter_by(corr_pe=2).first():
        return
    db.flush()
    db.execute(text("""
        INSERT INTO oferta_curso
            (cod_periodo, cod_fac, cod_esc, corr_pe, cod_curso, cod_seccion, vacantes, activo)
        SELECT oferta_curso.cod_periodo, oferta_curso.cod_fac, oferta_curso.cod_esc,
               oferta_curso.corr_pe, oferta_curso.cod_curso, s.seccion,
               oferta_curso.vacantes, oferta_curso.activo
        FROM oferta_curso
        JOIN periodo_academico USING (cod_periodo)
        CROSS JOIN (VALUES ('B'), ('C')) AS s(seccion)
        WHERE cod_seccion = 'A' AND periodo_academico.tipo_periodo <> 'VERANO'
        ON CONFLICT (cod_periodo, cod_fac, cod_esc, corr_pe, cod_curso, cod_seccion) DO NOTHING
    """))
    periodo = db.query(models.PeriodoAcademico).filter(
        models.PeriodoAcademico.activo.is_(True),
        models.PeriodoAcademico.tipo_periodo != "VERANO",
    ).order_by(
        models.PeriodoAcademico.fecha_inicio.desc(),
    ).first()
    if not periodo:
        activo = db.query(models.PeriodoAcademico).filter_by(activo=True).order_by(
            models.PeriodoAcademico.fecha_inicio.desc(),
        ).first()
        if activo:
            periodo = db.query(models.PeriodoAcademico).filter(
                models.PeriodoAcademico.tipo_periodo != "VERANO",
                models.PeriodoAcademico.fecha_inicio > activo.fecha_inicio,
            ).order_by(models.PeriodoAcademico.fecha_inicio).first()
    if not periodo:
        return
    cabecera = db.query(models.HorarioCabecera).filter_by(
        cod_periodo=periodo.cod_periodo, cod_fac=FACULTAD, cod_esc=ESCUELA, corr_pe=2,
    ).first()
    if not cabecera:
        cabecera = models.HorarioCabecera(
            cod_periodo=periodo.cod_periodo, cod_fac=FACULTAD, cod_esc=ESCUELA,
            corr_pe=2, fecha_creacion=date.today(),
        )
        db.add(cabecera)
        db.flush()
    nombres = ("Primer", "Segundo", "Tercer", "Cuarto", "Quinto", "Sexto", "Séptimo", "Octavo", "Noveno", "Décimo")
    for semestre in range(1, 11):
        if not db.query(models.HorarioDetalle).filter_by(
            id_horario=cabecera.id_horario, semestre_corr=semestre,
        ).first():
            db.add(models.HorarioDetalle(
                id_horario=cabecera.id_horario, semestre_corr=semestre,
                semestre_desc=f"{nombres[semestre - 1]} semestre",
            ))
    db.flush()

    dias = ("LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO")
    cursos = db.query(models.Curso).filter_by(corr_pe=2).order_by(
        models.Curso.semestre, models.Curso.cod_curso,
    ).all()
    por_semestre = {n: [c for c in cursos if c.semestre == n] for n in range(1, 11)}
    legado = db.query(models.HorarioCurso).filter_by(
        id_horario=cabecera.id_horario, semestre_corr=6, cod_seccion="A",
    ).all()
    codigos_legado = {"P19-39", "P19-40", "P19-41", "P19-42", "P19-43", "P19-44", "P19-45"}
    if (len(legado) == 10 and {item.cod_curso for item in legado} == codigos_legado
            and any((item.hora_fin.hour * 60 + item.hora_fin.minute
                     - item.hora_inicio.hour * 60 - item.hora_inicio.minute) % 50 for item in legado)):
        # Sustituye exclusivamente el horario demostrativo antiguo, que no respetaba bloques de 50 min.
        for item in legado:
            db.delete(item)
        db.flush()
    for semestre in range(1, 11):
        for seccion in ("A", "B", "C"):
            if db.query(models.HorarioCurso).filter_by(
                id_horario=cabecera.id_horario, semestre_corr=semestre, cod_seccion=seccion,
            ).first():
                continue
            if semestre <= 2 or (semestre == 3 and seccion != "C"):
                inicio, slots_dia = 8 * 60, 8
            elif semestre <= 5 or (semestre == 6 and seccion == "A") or semestre == 3:
                inicio, slots_dia = 13 * 60, 6
            else:
                inicio, slots_dia = 17 * 60 + 10, 6
            cursor = 0
            for item in por_semestre[semestre]:
                for tipo_sesion, horas in (("T", item.ht), ("P", item.hp)):
                    restantes = horas
                    while restantes > 0:
                        indice_dia, slot_dia = divmod(cursor, slots_dia)
                        if indice_dia >= len(dias):
                            raise RuntimeError(f"No hay espacio semanal para el ciclo {semestre}, sección {seccion}.")
                        bloque = min(restantes, slots_dia - slot_dia)
                        minuto_inicio = inicio + slot_dia * 50
                        minuto_fin = minuto_inicio + bloque * 50
                        db.add(models.HorarioCurso(
                            id_horario=cabecera.id_horario, semestre_corr=semestre,
                            cod_curso=item.cod_curso, cod_seccion=seccion,
                            tipo_sesion=tipo_sesion, cod_fac=FACULTAD, cod_esc=ESCUELA,
                            corr_pe=2, dia_semana=dias[indice_dia],
                            hora_inicio=time(minuto_inicio // 60, minuto_inicio % 60),
                            hora_fin=time(minuto_fin // 60, minuto_fin % 60),
                            aula=f"S{semestre:02d}-{seccion}",
                        ))
                        cursor += bloque
                        restantes -= bloque

    # Deja lista también la siguiente campaña regular. Así un alumno cuyo ciclo
    # no corresponde a la paridad del período activo puede preparar su próxima matrícula.
    siguiente = db.query(models.PeriodoAcademico).filter(
        models.PeriodoAcademico.tipo_periodo != "VERANO",
        models.PeriodoAcademico.fecha_inicio > periodo.fecha_inicio,
    ).order_by(models.PeriodoAcademico.fecha_inicio).first()
    if siguiente:
        cabecera_siguiente = db.query(models.HorarioCabecera).filter_by(
            cod_periodo=siguiente.cod_periodo, cod_fac=FACULTAD,
            cod_esc=ESCUELA, corr_pe=2,
        ).first()
        if not cabecera_siguiente:
            cabecera_siguiente = models.HorarioCabecera(
                cod_periodo=siguiente.cod_periodo, cod_fac=FACULTAD,
                cod_esc=ESCUELA, corr_pe=2, fecha_creacion=date.today(),
            )
            db.add(cabecera_siguiente)
            db.flush()
        for semestre in range(1, 11):
            if not db.query(models.HorarioDetalle).filter_by(
                id_horario=cabecera_siguiente.id_horario, semestre_corr=semestre,
            ).first():
                db.add(models.HorarioDetalle(
                    id_horario=cabecera_siguiente.id_horario, semestre_corr=semestre,
                    semestre_desc=f"{nombres[semestre - 1]} semestre",
                ))
        db.flush()
        if not db.query(models.HorarioCurso).filter_by(
            id_horario=cabecera_siguiente.id_horario,
        ).first():
            for sesion in db.query(models.HorarioCurso).filter_by(
                id_horario=cabecera.id_horario,
            ).all():
                db.add(models.HorarioCurso(
                    id_horario=cabecera_siguiente.id_horario,
                    semestre_corr=sesion.semestre_corr, cod_curso=sesion.cod_curso,
                    cod_seccion=sesion.cod_seccion, tipo_sesion=sesion.tipo_sesion,
                    cod_fac=sesion.cod_fac, cod_esc=sesion.cod_esc,
                    corr_pe=sesion.corr_pe, dia_semana=sesion.dia_semana,
                    hora_inicio=sesion.hora_inicio, hora_fin=sesion.hora_fin,
                    aula=sesion.aula,
                ))
    docentes = db.query(models.Docente).filter_by(cod_fac=FACULTAD, cod_esc=ESCUELA).order_by(
        models.Docente.cod_docente,
    ).all()
    if docentes:
        ofertas_sin_docente = db.query(models.OfertaCurso).filter_by(
            corr_pe=2, activo=True,
        ).order_by(models.OfertaCurso.cod_periodo, models.OfertaCurso.cod_curso, models.OfertaCurso.cod_seccion).all()
        for indice, oferta in enumerate(ofertas_sin_docente):
            if not oferta.cod_docente:
                oferta.cod_docente = docentes[indice % len(docentes)].cod_docente
    db.flush()


def asegurar_estudiantes_secciones(db):
    """Agrega alumnos demostrativos y los distribuye entre A, B y C sin alterar existentes."""
    if not db.query(models.PlanEstudio).filter_by(corr_pe=2).first():
        return
    alumnos = (
        ("2024001011", "71001011", "Alarcón Vega, María", 2, "A"),
        ("2023001022", "71001022", "Benavides Rojas, Luis", 4, "B"),
        ("2022001033", "71001033", "Cáceres Silva, Ana", 6, "C"),
        ("2021001044", "71001044", "Delgado Poma, José", 8, "A"),
        ("2020001055", "71001055", "Espinoza Torres, Carla", 10, "B"),
        ("2024001066", "71001066", "Flores Medina, Miguel", 2, "C"),
        ("2024001077", "71001077", "Gamarra León, Sofía", 2, "B"),
        ("2024001088", "71001088", "Herrera Campos, Diego", 2, "C"),
        ("2023001099", "71001099", "Ibarra Salas, Lucía", 4, "A"),
        ("2023001100", "71001100", "Jiménez Ríos, Carlos", 4, "C"),
        ("2022001111", "71001111", "López Vargas, Daniela", 6, "A"),
        ("2022001122", "71001122", "Mendoza Paredes, Bruno", 6, "B"),
        ("2021001133", "71001133", "Núñez Castro, Paula", 8, "B"),
        ("2021001144", "71001144", "Ochoa Ruiz, Fernando", 8, "C"),
        ("2020001155", "71001155", "Peña Soto, Valentina", 10, "A"),
        ("2020001166", "71001166", "Quispe Díaz, Andrés", 10, "C"),
        ("2024001177", "71001177", "Ramírez Luna, Camila", 2, "A"),
        ("2023001188", "71001188", "Salazar Meza, Joaquín", 4, "B"),
        ("2024001199", "71001199", "Sánchez Ortiz, Elena", 2, "B"),
        ("2023001200", "71001200", "Valdivia Ramos, Mateo", 4, "A"),
        ("2022001211", "71001211", "Zegarra Núñez, Andrea", 6, "B"),
        ("2021001222", "71001222", "Campos Huamán, Rodrigo", 8, "C"),
        ("2020001233", "71001233", "Chávez Flores, Mariana", 10, "A"),
        ("2024001244", "71001244", "Ramos Ponce, Thiago", 2, "C"),
    )
    periodo = db.query(models.PeriodoAcademico).filter_by(activo=True).first()
    # Estas cuentas quedan libres para demostrar la prematrícula antes del registro oficial.
    estudiantes_prematricula = {"2024001077", "2024001088", "2023001099"}
    for codigo, dni, nombre, ciclo, seccion in alumnos:
        estudiante = db.query(models.Estudiante).filter_by(cod_estudiante=codigo).first()
        if not estudiante:
            estudiante = models.Estudiante(
                cod_estudiante=codigo, dni=dni, apellidos_nombres=nombre,
                correo=f"{codigo}@unfv.edu.pe", cod_fac=FACULTAD, cod_esc=ESCUELA,
                corr_pe=2, ciclo_actual=ciclo, estado="ACTIVO",
            )
            db.add(estudiante)
            db.flush()
        auth.ensure_student_user(db, estudiante)
        if codigo in estudiantes_prematricula:
            continue
        if not periodo or db.query(models.Matricula).filter_by(
            cod_estudiante=codigo, cod_periodo=periodo.cod_periodo,
        ).first():
            continue
        ofertas = (db.query(models.OfertaCurso).join(
            models.Curso,
            (models.Curso.corr_pe == models.OfertaCurso.corr_pe)
            & (models.Curso.cod_curso == models.OfertaCurso.cod_curso)
            & (models.Curso.cod_fac == models.OfertaCurso.cod_fac)
            & (models.Curso.cod_esc == models.OfertaCurso.cod_esc),
        ).filter(
            models.OfertaCurso.cod_periodo == periodo.cod_periodo,
            models.OfertaCurso.corr_pe == 2,
            models.OfertaCurso.cod_seccion == seccion,
            models.Curso.semestre == ciclo,
        ).order_by(models.Curso.cod_curso).limit(3).all())
        if not ofertas:
            continue
        matricula = models.Matricula(
            cod_estudiante=codigo, cod_periodo=periodo.cod_periodo,
            cod_fac=FACULTAD, cod_esc=ESCUELA, corr_pe=2,
            ciclo_matricula=ciclo, fecha_matricula=date.today(), estado="REGISTRADA",
        )
        db.add(matricula)
        db.flush()
        for oferta in ofertas:
            db.add(models.MatriculaDetalle(
                id_matricula=matricula.id_matricula, id_oferta=oferta.id_oferta,
                resultado="MATRICULADO",
            ))
    asegurar_historial_demostrativo(db, alumnos)


def asegurar_historial_demostrativo(db, alumnos):
    """Crea historiales completos únicamente para las cuentas demostrativas."""
    periodo = db.query(models.PeriodoAcademico).filter_by(cod_periodo="2025-I").first()
    if not periodo:
        return
    db.flush()
    for indice_alumno, (codigo, _, _, ciclo_actual, seccion) in enumerate(alumnos):
        if db.query(models.Matricula).filter_by(
            cod_estudiante=codigo, cod_periodo=periodo.cod_periodo,
        ).first():
            continue
        ciclo_historial = max(1, ciclo_actual - 1)
        ofertas = (
            db.query(models.OfertaCurso)
            .join(models.Curso, (
                (models.Curso.cod_fac == models.OfertaCurso.cod_fac)
                & (models.Curso.cod_esc == models.OfertaCurso.cod_esc)
                & (models.Curso.corr_pe == models.OfertaCurso.corr_pe)
                & (models.Curso.cod_curso == models.OfertaCurso.cod_curso)
            ))
            .filter(
                models.OfertaCurso.cod_periodo == periodo.cod_periodo,
                models.OfertaCurso.corr_pe == 2,
                models.OfertaCurso.cod_seccion == seccion,
                models.Curso.semestre == ciclo_historial,
            )
            .order_by(models.Curso.cod_curso)
            .all()
        )
        if not ofertas:
            continue
        matricula = models.Matricula(
            cod_estudiante=codigo, cod_periodo=periodo.cod_periodo,
            cod_fac=FACULTAD, cod_esc=ESCUELA, corr_pe=2,
            ciclo_matricula=ciclo_historial, fecha_matricula=periodo.fecha_inicio,
            estado="CERRADA",
        )
        db.add(matricula)
        db.flush()
        for indice_curso, oferta in enumerate(ofertas):
            if indice_alumno % 4 == 1 and indice_curso == len(ofertas) - 1:
                practicas, parcial, examen = 8, 10, 9
            else:
                practicas = 12 + (indice_alumno + indice_curso) % 8
                parcial = 11 + (indice_alumno * 2 + indice_curso) % 9
                examen = 10 + (indice_alumno + indice_curso * 2) % 10
            promedio = int(practicas * .40 + parcial * .30 + examen * .30 + .5)
            db.add(models.MatriculaDetalle(
                id_matricula=matricula.id_matricula,
                id_oferta=oferta.id_oferta,
                nota_practicas=practicas,
                nota_parcial=parcial,
                nota_examen_final=examen,
                nota_final=promedio,
                resultado="APROBADO" if promedio >= 11 else "DESAPROBADO",
            ))


def insertar_periodos_y_ofertas(db):
    periodos = [
        ("2024-V", "Ciclo de verano 2024", 2024, "VERANO", date(2024, 1, 8), date(2024, 2, 29), False),
        ("2024-I", "Semestre académico 2024-I", 2024, "I", date(2024, 3, 18), date(2024, 7, 20), False),
        ("2024-II", "Semestre académico 2024-II", 2024, "II", date(2024, 8, 19), date(2024, 12, 21), False),
        ("2025-V", "Ciclo de verano 2025", 2025, "VERANO", date(2025, 1, 6), date(2025, 2, 28), False),
        ("2025-I", "Semestre académico 2025-I", 2025, "I", date(2025, 3, 17), date(2025, 7, 19), False),
        ("2025-II", "Semestre académico 2025-II", 2025, "II", date(2025, 8, 18), date(2025, 12, 20), False),
        ("2026-V", "Ciclo de verano 2026", 2026, "VERANO", date(2026, 1, 5), date(2026, 2, 28), False),
        ("2026-I", "Semestre académico 2026-I", 2026, "I", date(2026, 3, 16), date(2026, 7, 18), False),
        ("2026-II", "Semestre académico 2026-II", 2026, "II", date(2026, 8, 17), date(2026, 12, 19), True),
    ]
    for codigo, nombre, anio, tipo, inicio, fin, activo in periodos:
        existente = db.query(models.PeriodoAcademico).filter_by(cod_periodo=codigo).first()
        if not existente:
            db.add(models.PeriodoAcademico(
                cod_periodo=codigo, den_periodo=nombre, anio=anio, tipo_periodo=tipo,
                fecha_inicio=inicio, fecha_fin=fin, activo=activo,
            ))
    db.flush()

    cursos = db.query(models.Curso).all()
    for codigo, _, _, tipo, *_ in periodos:
        if tipo == "VERANO":
            continue
        for item in cursos:
            db.add(models.OfertaCurso(
                cod_periodo=codigo, cod_fac=item.cod_fac, cod_esc=item.cod_esc,
                corr_pe=item.corr_pe, cod_curso=item.cod_curso, cod_seccion="A",
                vacantes=35, activo=True,
            ))
    db.flush()


def insertar_estudiante_demo(db):
    estudiante = models.Estudiante(
        cod_estudiante="2021000001", dni="71234567",
        apellidos_nombres="Pérez Quispe, Juan Carlos",
        correo="2021000001@unfv.edu.pe", cod_fac=FACULTAD, cod_esc=ESCUELA,
        corr_pe=2, ciclo_actual=6, estado="ACTIVO",
    )
    db.add(estudiante)
    db.flush()
    auth.ensure_student_user(db, estudiante)

    historial = [
        ("2024-I", "P19-24", 15, "APROBADO"),
        ("2025-I", "P19-33", 8, "DESAPROBADO"),
    ]
    for periodo, codigo, nota, resultado in historial:
        oferta = db.query(models.OfertaCurso).filter_by(
            cod_periodo=periodo, corr_pe=2, cod_curso=codigo, cod_seccion="A",
        ).one()
        matricula = models.Matricula(
            cod_estudiante=estudiante.cod_estudiante, cod_periodo=periodo,
            cod_fac=FACULTAD, cod_esc=ESCUELA, corr_pe=2,
            ciclo_matricula=6, fecha_matricula=date(int(periodo[:4]), 3, 10),
            estado="CERRADA",
        )
        db.add(matricula)
        db.flush()
        db.add(models.MatriculaDetalle(
            id_matricula=matricula.id_matricula, id_oferta=oferta.id_oferta,
            nota_practicas=nota, nota_parcial=nota, nota_examen_final=nota,
            nota_final=nota, resultado=resultado,
        ))

    adicionales = [
        ("2026000001", "70000001", "Rojas Salazar, Andrea", 1),
        ("2025000002", "70000002", "Mendoza Ruiz, Diego", 2),
        ("2025000003", "70000003", "Castro Vega, Lucía", 3),
        ("2024000004", "70000004", "Navarro Flores, Martín", 4),
        ("2024000005", "70000005", "Quispe León, Valeria", 5),
        ("2023000007", "70000007", "Paredes Soto, Renato", 7),
        ("2022000008", "70000008", "Torres Campos, Daniela", 8),
        ("2021000009", "70000009", "Ramírez Peña, Sebastián", 9),
        ("2020000010", "70000010", "García Núñez, Camila", 10),
    ]
    for codigo, dni, nombre, ciclo in adicionales:
        item = models.Estudiante(
            cod_estudiante=codigo, dni=dni, apellidos_nombres=nombre,
            correo=f"{codigo}@unfv.edu.pe", cod_fac=FACULTAD, cod_esc=ESCUELA,
            corr_pe=2, ciclo_actual=ciclo, estado="ACTIVO",
        )
        db.add(item)
        db.flush()
        auth.ensure_student_user(db, item)


def seed_data(reset=False):
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    # Una base anterior puede tener perfil sin la columna de permisos.
    # Migrar antes de consultar perfiles; no elimina ni reinicia datos.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE perfil ADD COLUMN IF NOT EXISTS permisos VARCHAR(500) NOT NULL DEFAULT ''"
        )
        connection.exec_driver_sql(
            "ALTER TABLE estudiante ADD COLUMN IF NOT EXISTS prematricula VARCHAR(1000) NOT NULL DEFAULT ''"
        )
        connection.exec_driver_sql(
            "ALTER TABLE oferta_curso ADD COLUMN IF NOT EXISTS cod_docente VARCHAR(20)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE matricula_detalle ADD COLUMN IF NOT EXISTS nota_practicas INTEGER"
        )
        connection.exec_driver_sql(
            "ALTER TABLE matricula_detalle ADD COLUMN IF NOT EXISTS nota_parcial INTEGER"
        )
        connection.exec_driver_sql(
            "ALTER TABLE matricula_detalle ADD COLUMN IF NOT EXISTS nota_examen_final INTEGER"
        )
        connection.exec_driver_sql("""
            UPDATE matricula_detalle
            SET nota_practicas = COALESCE(nota_practicas, nota_final),
                nota_parcial = COALESCE(nota_parcial, nota_final),
                nota_examen_final = COALESCE(nota_examen_final, nota_final)
            WHERE nota_final IS NOT NULL
              AND (nota_practicas IS NULL OR nota_parcial IS NULL OR nota_examen_final IS NULL)
        """)
        connection.exec_driver_sql("""
            UPDATE plan_estudio
            SET den_plan = CASE
                WHEN anio_plan = 2010 THEN 'Plan Curricular 2010'
                WHEN anio_plan = 2019 THEN 'Plan de Estudios 2019'
                ELSE den_plan
            END
            WHERE anio_plan IN (2010, 2019)
        """)
    migrar_periodos_y_ofertas()
    migrar_codigos_estudiante()
    inicializar_estudiantes_primer_ciclo()
    reparar_avance_ciclos()
    db = SessionLocal()
    try:
        auth.ensure_security_data(db)
        if db.query(models.PlanEstudio).first():
            asegurar_horarios_y_secciones(db)
            asegurar_estudiantes_secciones(db)
            db.commit()
            print("La base ya contiene planes; se conservaron los datos existentes.")
            return
        db.add(models.Facultad(cod_fac=FACULTAD, den_fac="Facultad de Ingeniería Industrial y de Sistemas"))
        db.add(models.Escuela(cod_fac=FACULTAD, cod_esc=ESCUELA, den_escuela="Ingeniería de Sistemas"))
        db.flush()
        insertar_plan(db, 1, {
            "cod_fac": FACULTAD, "cod_esc": ESCUELA, "corr_pe": 1,
            "den_plan": "Plan Curricular 2010", "anio_plan": 2010,
            "fecha_vigencia": date(2010, 3, 15), "fecha_baja": date(2018, 12, 31), "vigente": False,
        }, CURSOS_2010, PREREQUISITOS_2010)
        insertar_plan(db, 2, {
            "cod_fac": FACULTAD, "cod_esc": ESCUELA, "corr_pe": 2,
            "den_plan": "Plan de Estudios 2019", "anio_plan": 2019,
            "fecha_vigencia": date(2019, 1, 1), "fecha_baja": None, "vigente": True,
        }, construir_cursos_2019(), PREREQUISITOS_2019)
        insertar_docentes(db)
        insertar_periodos_y_ofertas(db)
        insertar_estudiante_demo(db)
        asegurar_horarios_y_secciones(db)
        asegurar_estudiantes_secciones(db)
        db.commit()
        print("Datos cargados: mallas, períodos 2024-2026, ofertas, estudiante e historial demostrativo.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Recrea el esquema completo (elimina datos existentes).")
    args = parser.parse_args()
    seed_data(reset=args.reset)
