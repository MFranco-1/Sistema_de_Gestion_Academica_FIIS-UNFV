# Sistema de Gestión Académica FIIS–UNFV

Aplicación web de la Facultad de Ingeniería Industrial y de Sistemas de la UNFV para consultar y mantener las mallas curriculares 2010 y 2019 de Ingeniería de Sistemas.

## Funcionalidades

- Filtros encadenados desde PostgreSQL: malla → semestre → cursos → detalle.
- Detalle del curso con créditos, horas, tipo, prerrequisitos y cursos dependientes.
- Resumen SQL por semestre: cursos, créditos, horas, tipos y presencia de prerrequisitos.
- Consulta de programación académica y plana docente.
- Mantenimiento transaccional de cursos, prerrequisitos y sesiones de horario.
- CRUD de estudiantes y asignación de malla y ciclo académico.
- Matrícula validada por oferta anual, período I/II/verano, historial y prerrequisitos.
- Registro de notas y resultados para cursos aprobados, desaprobados o retirados.
- Login institucional con perfiles Administrador y Estudiante, cambio de perfil dentro del panel y permisos por endpoint.
- Administración separada de usuarios y perfiles, con activación de cuentas, vínculo con estudiantes y nombres de perfil editables.
- Validación de duplicados, semestres, créditos, horas, precedencia académica y cruces de aula/sección.
- Documentación interactiva de la API con Swagger.

## Modelo de datos

El modelo mantiene diecisiete tablas:

1. `facultad`
2. `escuela`
3. `docente`
4. `plan_estudio`
5. `curso`
6. `curso_prerequisito`
7. `periodo_academico`
8. `horario_cabecera`
9. `horario_detalle`
10. `horario_curso`
11. `estudiante`
12. `oferta_curso`
13. `matricula`
14. `matricula_detalle`
15. `perfil`
16. `usuario`
17. `usuario_perfil`

No existe una tabla `plan_semestre`. Los semestres de cada malla se obtienen con `SELECT DISTINCT curso.semestre`.

## Tecnologías

- PostgreSQL
- Python 3.10 o superior
- FastAPI, SQLAlchemy y pg8000
- Angular 16

## Ejecución

### Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
$env:PGPASSWORD='tu_clave_local'
$env:DATABASE_URL='postgresql+pg8000://postgres:tu_clave_local@localhost:5432/universidad_db'
$env:AUTH_SECRET='una-clave-larga-y-privada'
$env:ADMIN_PASSWORD='una-clave-segura'
python init_db.py
python seed_db.py
uvicorn app.main:app --reload --port 8000
```

La opción `python seed_db.py --reset` elimina y recrea el esquema. Úsela solamente sobre una base de prueba o cuando sea aceptable descartar sus datos.

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

La conexión puede cambiarse sin modificar código:

```powershell
$env:DATABASE_URL='postgresql+pg8000://usuario:clave@localhost:5432/base_prueba'
```

En desarrollo, si no se configuran variables, la cuenta inicial es `admin` con contraseña `Admin123*`. En Render se deben definir `ADMIN_PASSWORD` y `AUTH_SECRET` con valores privados antes del primer arranque.

Al registrar un estudiante, el sistema crea su cuenta con el código de estudiante como usuario y el DNI como contraseña temporal. El administrador puede cambiar la contraseña, activar o desactivar la cuenta y asignarle uno o ambos perfiles desde Mantenimiento académico.

### Frontend

```powershell
cd frontend
npm install
npm start
```

Interfaz: `http://localhost:4200`.

## Despliegue

- Backend Render: `https://sistema-academico-unfv-api.onrender.com`
- En Render, `DATABASE_URL` acepta tanto `postgresql://` como `postgresql+pg8000://`.
- Después de desplegar Vercel, configurar en Render `CORS_ORIGINS=https://TU-PROYECTO.vercel.app`.
- En Vercel usar `frontend` como Root Directory, `npm run build` y `dist/frontend` como Output Directory.

## Endpoints principales

### Consulta

- `GET /planes/`
- `GET /semestres/?corr_pe=2`
- `GET /cursos/?corr_pe=2&semestre=6`
- `GET /cursos/{cod_curso}/detalle?corr_pe=2`
- `GET /resumen-semestre/?corr_pe=2&semestre=6`
- `GET /periodos/`
- `GET /horarios/?corr_pe=2&semestre=6&cod_periodo=2026-II`
- `GET /programacion/?corr_pe=2&semestre=6&cod_periodo=2026-II`
- `GET /docentes/`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/cambiar-perfil`
- `GET /estudiantes/`
- `GET /estudiantes/{codigo}/ofertas?cod_periodo=2026-I`
- `GET /estudiantes/{codigo}/matriculas`

### Mantenimiento

- `POST /cursos/`
- `PUT /cursos/{cod_curso}?corr_pe=...`
- `DELETE /cursos/{cod_curso}?corr_pe=...`
- `POST /prerrequisitos/`
- `DELETE /prerrequisitos/{corr_pe}/{cod_curso}/{cod_requisito}`
- `POST /sesiones/`
- `PUT /sesiones/`
- `POST /estudiantes/`
- `PUT /estudiantes/{codigo}`
- `DELETE /estudiantes/{codigo}`
- `POST /matriculas/`
- `PUT /matriculas/{id}/ofertas/{id_oferta}/resultado`
- `GET /usuarios/`
- `POST /usuarios/`
- `PUT /usuarios/{id}`
- `DELETE /usuarios/{id}`
- `GET /perfiles/`
- `PUT /perfiles/{id}`

Las mutaciones usan transacciones. Los errores de validación se devuelven como HTTP 422 y los conflictos de integridad o cruces como HTTP 409.

## Scripts de base de datos

- `database/01_esquema.sql`: definición física completa de las tablas, claves, restricciones, índices y perfiles.
- `database/02_consultas_demostracion.sql`: semestres, detalle, dependencias, resumen y controles de horario/eliminación.
- `database/03_diccionario_datos.md`: descripción de tablas y reglas de integridad.

Solo existen dos archivos SQL: el esquema consolidado y las consultas demostrativas. Para bases existentes, SQLAlchemy crea de forma no destructiva las tablas de seguridad al iniciar el backend.

## Datos académicos incluidos

Se conservan las mallas 2010 y 2019, sus cursos, créditos y prerrequisitos, la plana docente y el horario demostrativo. También se incluyen períodos 2024–2026, ofertas regulares por paridad de ciclo, ofertas de verano y estudiantes demostrativos distribuidos entre los ciclos I y X. El estudiante de sexto ciclo incluye un curso aprobado y otro desaprobado.
