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
- Portal estudiantil con Mi matrícula, Historial y Mi malla; muestra créditos y prerrequisitos aplicables.
- Períodos académicos futuros y ofertas generados de forma incremental, incluyendo verano 2024.
- Cierre de notas en lote: 0–10 desaprobado, 11–20 aprobado y avance automático de ciclo cuando corresponde.
- Registro de notas y resultados para cursos aprobados, desaprobados o retirados.
- Login institucional con perfiles Administrador y Estudiante, cambio de perfil dentro del panel y permisos por endpoint.
- Administración separada de usuarios y perfiles, con activación de cuentas, vínculo con estudiantes y nombres de perfil editables.
- Perfiles personalizados con permisos configurables, asignación dinámica a usuarios y gestión administrativa de matrículas e historial.
- Códigos estudiantiles de exactamente 10 dígitos; las cuentas estudiantiles se inicializan obligatoriamente con el DNI como contraseña.
- Validación de duplicados, semestres, créditos, horas, precedencia académica y cruces de aula/sección.
- Perfil estudiantil con foto local, ciclo, carrera, código, créditos y horarios disponibles; la malla permite navegar con el mouse hacia sus prerrequisitos.
- Programación A/B/C por ciclo y turno, horas académicas de 50 minutos, apertura de secciones y capacidad por curso/sección.
- Gestión de horarios en pantalla independiente: teoría y práctica se programan juntas según las horas de la malla, dentro de una misma sección y aula.
- Asignación de docentes por curso, período y sección para los perfiles autorizados.
- El alumno visualiza el docente de cada sección antes de matricularse, en su prematrícula y en el historial académico.
- Prematrícula estudiantil persistente con vista semanal institucional; funciona como guía y no altera la matrícula oficial.
- La matrícula muestra un resumen lateral de cursos y créditos, solicita confirmación y permite descargar una constancia PDF por período.
- El historial presenta prácticas (40 %), parcial (30 %), examen final (30 %), promedio final, promedio aritmético y promedio ponderado.
- Perfiles institucionales adicionales: Jefe de departamento, Director de escuela y Administración.
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

1. Sube los cambios a GitHub. `frontend/node_modules`, `frontend/dist`, `frontend/.angular` y los archivos `.log` están excluidos por `.gitignore`; no se despliegan.
2. En Render, crea un **Web Service** Python desde este repositorio con Root Directory `backend`, Build Command `pip install -r requirements.txt` y Start Command `python seed_db.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. El seed es incremental e idempotente; no elimina datos existentes.
3. En **Environment** del servicio Render configura `DATABASE_URL` con la **Internal Database URL** de tu PostgreSQL de Render (en la misma región), `AUTH_SECRET` con una clave larga y aleatoria, `ADMIN_PASSWORD` con una clave privada y `CORS_ORIGINS` con la URL exacta que te dé Vercel. La aplicación acepta URLs `postgresql://` y `postgresql+pg8000://`.
4. Antes de desplegar Vercel, cambia `frontend/src/environments/environment.production.ts` para que `apiUrl` sea la nueva URL pública de Render, sin `/` final. Este valor queda incorporado en el build de Angular; no basta con crear una variable en Vercel.
5. En Vercel, importa el mismo repositorio como proyecto **Angular** con Root Directory `frontend`, Build Command `npm run build` y Output Directory `dist/frontend`. El archivo `frontend/vercel.json` permite abrir directamente rutas como `/login`.
6. Comprueba `https://TU-API.onrender.com/`, luego abre la URL de Vercel e inicia sesión. Si cambia el dominio de Vercel, actualiza `CORS_ORIGINS` en Render y vuelve a desplegar el backend.

No ejecutes `seed_db.py --reset` sobre una base con datos. Si la base de Render es nueva, carga `database/01_esquema.sql` y los datos iniciales con `seed_db.py` una sola vez; no repitas la carga sobre una base existente.

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
- `POST /matriculas/`
- `PUT /matriculas/{id}/ofertas/{id_oferta}/resultado`
- `PUT /matriculas/{id}/resultados`

### Mantenimiento

- `POST /cursos/`
- `PUT /cursos/{cod_curso}?corr_pe=...`
- `DELETE /cursos/{cod_curso}?corr_pe=...`
- `POST /prerrequisitos/`
- `DELETE /prerrequisitos/{corr_pe}/{cod_curso}/{cod_requisito}`
- `POST /sesiones/`
- `PUT /sesiones/`
- `PUT /horarios/cursos`
- `POST /ofertas/secciones`
- `GET /ofertas/?cod_periodo=2026-II&corr_pe=2&semestre=2`
- `PUT /ofertas/{id_oferta}/docente`
- `GET /estudiantes/{codigo}/prematricula`
- `PUT /estudiantes/{codigo}/prematricula`
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
- `POST /perfiles/`
- `PUT /perfiles/{id}`
- `DELETE /perfiles/{id}`

Las mutaciones usan transacciones. Los errores de validación se devuelven como HTTP 422 y los conflictos de integridad o cruces como HTTP 409.

## Scripts de base de datos

- `database/01_esquema.sql`: definición física completa de las tablas, claves, restricciones, índices y perfiles.
- `database/02_consultas_demostracion.sql`: semestres, detalle, dependencias, resumen y controles de horario/eliminación.
- `database/03_diccionario_datos.md`: descripción de tablas y reglas de integridad.

Solo existen dos archivos SQL: el esquema consolidado y las consultas demostrativas. Para bases existentes, SQLAlchemy crea de forma no destructiva las tablas de seguridad al iniciar el backend.

## Datos académicos incluidos

Se conservan las mallas 2010 y 2019, sus cursos, créditos y prerrequisitos, la plana docente y el horario demostrativo. También se incluyen períodos 2024–2026, ofertas regulares por paridad de ciclo, ofertas de verano y estudiantes demostrativos distribuidos entre los ciclos I y X. El estudiante de sexto ciclo incluye un curso aprobado y otro desaprobado.
