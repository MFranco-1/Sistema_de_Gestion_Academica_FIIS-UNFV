import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Facultad { cod_fac: number; den_fac: string; }
export interface Escuela { cod_fac: number; cod_esc: number; den_escuela: string; }
export interface Docente {
  cod_fac: number;
  cod_esc: number;
  cod_docente: string;
  apellidos_nombres: string;
  categoria: string;
  dedicacion: string;
  departamento: string;
  fuente: string;
}

export interface PlanEstudio {
  cod_fac: number;
  cod_esc: number;
  corr_pe: number;
  den_plan: string;
  anio_plan: number;
  fecha_vigencia: string;
  fecha_baja?: string;
  vigente: boolean;
  total_cursos: number;
  total_creditos: number;
}

export interface Curso {
  cod_fac: number;
  cod_esc: number;
  corr_pe: number;
  cod_curso: string;
  den_curso: string;
  semestre: number;
  ht: number;
  hp: number;
  cred: number;
  tipo_curso: string;
  prerrequisitos_nombres: string;
}

export interface CursoRelacionado {
  cod_curso: string;
  den_curso: string;
  semestre: number;
}

export interface CursoDetalle extends Curso {
  den_plan: string;
  anio_plan: number;
  prerrequisitos: CursoRelacionado[];
  cursos_dependientes: CursoRelacionado[];
}

export interface ResumenSemestre {
  corr_pe: number;
  semestre: number;
  total_cursos: number;
  total_creditos: number;
  horas_teoricas: number;
  horas_practicas: number;
  cursos_obligatorios: number;
  cursos_electivos: number;
  cursos_con_prerrequisitos: number;
  cursos_sin_prerrequisitos: number;
}

export interface CursoPayload {
  cod_fac?: number;
  cod_esc?: number;
  corr_pe: number;
  cod_curso: string;
  den_curso: string;
  semestre: number;
  ht: number;
  hp: number;
  cred: number;
  tipo_curso: string;
}

export interface PrerequisitoPayload {
  cod_fac?: number;
  cod_esc?: number;
  corr_pe: number;
  cod_curso: string;
  cod_curso_prerequisito: string;
}

export interface PeriodoAcademico {
  cod_periodo: string;
  den_periodo: string;
  anio: number;
  tipo_periodo: 'I' | 'II' | 'VERANO';
  fecha_inicio: string;
  fecha_fin: string;
  activo: boolean;
}

export interface ProgramacionHorario {
  id_horario: number;
  cod_periodo: string;
  corr_pe: number;
  den_plan: string;
  semestre_corr: number;
  semestre_desc: string;
  cod_curso: string;
  den_curso: string;
  cod_seccion: string;
  tipo_sesion: string;
  dia_semana: string;
  hora_inicio: string;
  hora_fin: string;
  aula: string;
}

export interface HorarioDisponible {
  id_horario: number;
  cod_periodo: string;
  corr_pe: number;
  semestre_corr: number;
  semestre_desc: string;
}

export interface SesionPayload {
  id_horario: number;
  semestre_corr: number;
  cod_curso: string;
  cod_seccion: string;
  tipo_sesion: string;
  cod_fac?: number;
  cod_esc?: number;
  corr_pe: number;
  dia_semana: string;
  hora_inicio: string;
  hora_fin: string;
  aula: string;
}

export interface SesionLocator {
  id_horario: number;
  semestre_corr: number;
  cod_curso: string;
  cod_seccion: string;
  tipo_sesion: string;
  dia_semana: string;
  hora_inicio: string;
}

export interface Mensaje { mensaje: string; }

export interface Estudiante {
  cod_estudiante: string;
  dni: string;
  apellidos_nombres: string;
  correo: string;
  cod_fac: number;
  cod_esc: number;
  corr_pe: number;
  ciclo_actual: number;
  estado: 'ACTIVO' | 'EGRESADO' | 'RETIRADO';
  den_plan: string;
  anio_ingreso: number;
  creditos_aprobados: number;
  creditos_matriculados: number;
}

export type EstudiantePayload = Omit<Estudiante, 'den_plan' | 'anio_ingreso' | 'creditos_aprobados' | 'creditos_matriculados'>;

export interface OfertaCurso {
  id_oferta: number;
  cod_periodo: string;
  corr_pe: number;
  cod_curso: string;
  den_curso: string;
  semestre: number;
  cred: number;
  cod_seccion: string;
  vacantes: number;
  matriculados: number;
  vacantes_disponibles: number;
  disponible: boolean;
  motivo: string;
  horario_resumen: string;
  horarios: BloqueHorario[];
  cod_docente?: string;
  docente_nombre: string;
}

export interface BloqueHorario { dia_semana: string; hora_inicio: string; hora_fin: string; tipo_sesion: string; aula: string; }

export interface OfertaAdministracion {
  id_oferta: number; cod_periodo: string; corr_pe: number; cod_curso: string;
  den_curso: string; semestre: number; ht: number; hp: number; cod_seccion: string;
  vacantes: number; cod_docente?: string; docente_nombre: string;
}

export interface ProgramacionCursoPayload {
  id_horario: number; semestre_corr: number; corr_pe: number; cod_curso: string;
  cod_seccion: string; aula: string;
  teoria?: { dia_semana: string; hora_inicio: string };
  practica?: { dia_semana: string; hora_inicio: string };
}

export interface Prematricula { cod_periodo: string; ofertas: number[]; }

export interface OfertaSeccionPayload {
  cod_periodo: string;
  corr_pe: number;
  cod_curso: string;
  cod_seccion: string;
  vacantes: number;
}

export interface MatriculaDetalle {
  id_matricula: number;
  id_oferta: number;
  cod_periodo: string;
  cod_curso: string;
  den_curso: string;
  semestre: number;
  cod_seccion: string;
  cod_docente?: string;
  docente_nombre: string;
  cred: number;
  nota_practicas?: number;
  nota_parcial?: number;
  nota_examen_final?: number;
  nota_final?: number;
  resultado: 'MATRICULADO' | 'APROBADO' | 'DESAPROBADO' | 'RETIRADO';
}

export interface MatriculaResumen {
  id_matricula: number;
  cod_estudiante: string;
  cod_periodo: string;
  ciclo_matricula: number;
  fecha_matricula: string;
  estado: string;
  total_creditos: number;
  promedio_aritmetico?: number;
  promedio_ponderado?: number;
  detalles: MatriculaDetalle[];
}

export interface UsuarioAdministracion {
  id_usuario: number;
  nombre_usuario: string;
  nombre_mostrar: string;
  cod_estudiante?: string;
  perfiles: string[];
  activo: boolean;
}

export interface UsuarioPayload {
  nombre_usuario?: string;
  clave?: string;
  nombre_mostrar: string;
  cod_estudiante?: string;
  perfiles: string[];
  activo: boolean;
}

export interface PerfilAdministracion {
  id_perfil: number;
  codigo: string;
  nombre: string;
  permisos: string[];
  total_usuarios: number;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private apiUrl = environment.apiUrl;
  constructor(private http: HttpClient) { }

  getPlanes(codFac = 1, codEsc = 1): Observable<PlanEstudio[]> {
    const params = new HttpParams().set('cod_fac', codFac).set('cod_esc', codEsc);
    return this.http.get<PlanEstudio[]>(`${this.apiUrl}/planes/`, { params });
  }

  getDocentes(buscar?: string, categoria?: string): Observable<Docente[]> {
    let params = new HttpParams();
    if (buscar?.trim()) params = params.set('buscar', buscar.trim());
    if (categoria) params = params.set('categoria', categoria);
    return this.http.get<Docente[]>(`${this.apiUrl}/docentes/`, { params });
  }

  getCursos(corrPe: number, semestre?: number, buscar?: string): Observable<Curso[]> {
    let params = new HttpParams().set('cod_fac', 1).set('cod_esc', 1).set('corr_pe', corrPe);
    if (semestre) params = params.set('semestre', semestre);
    if (buscar?.trim()) params = params.set('buscar', buscar.trim());
    return this.http.get<Curso[]>(`${this.apiUrl}/cursos/`, { params });
  }

  getSemestres(corrPe: number): Observable<number[]> {
    return this.http.get<number[]>(`${this.apiUrl}/semestres/`, {
      params: new HttpParams().set('corr_pe', corrPe)
    });
  }

  getCursoDetalle(corrPe: number, codCurso: string): Observable<CursoDetalle> {
    return this.http.get<CursoDetalle>(`${this.apiUrl}/cursos/${encodeURIComponent(codCurso)}/detalle`, {
      params: new HttpParams().set('corr_pe', corrPe)
    });
  }

  getResumenSemestre(corrPe: number, semestre: number): Observable<ResumenSemestre> {
    const params = new HttpParams().set('corr_pe', corrPe).set('semestre', semestre);
    return this.http.get<ResumenSemestre>(`${this.apiUrl}/resumen-semestre/`, { params });
  }

  crearCurso(curso: CursoPayload): Observable<Curso> {
    return this.http.post<Curso>(`${this.apiUrl}/cursos/`, curso);
  }

  editarCurso(corrPe: number, codCurso: string, curso: Omit<CursoPayload, 'corr_pe' | 'cod_curso'>): Observable<Curso> {
    return this.http.put<Curso>(`${this.apiUrl}/cursos/${encodeURIComponent(codCurso)}`, curso, {
      params: new HttpParams().set('corr_pe', corrPe)
    });
  }

  eliminarCurso(corrPe: number, codCurso: string): Observable<Mensaje> {
    return this.http.delete<Mensaje>(`${this.apiUrl}/cursos/${encodeURIComponent(codCurso)}`, {
      params: new HttpParams().set('corr_pe', corrPe)
    });
  }

  agregarPrerequisito(datos: PrerequisitoPayload): Observable<Mensaje> {
    return this.http.post<Mensaje>(`${this.apiUrl}/prerrequisitos/`, datos);
  }

  retirarPrerequisito(corrPe: number, codCurso: string, codRequisito: string): Observable<Mensaje> {
    return this.http.delete<Mensaje>(
      `${this.apiUrl}/prerrequisitos/${corrPe}/${encodeURIComponent(codCurso)}/${encodeURIComponent(codRequisito)}`
    );
  }

  getPeriodos(): Observable<PeriodoAcademico[]> {
    return this.http.get<PeriodoAcademico[]>(`${this.apiUrl}/periodos/`);
  }

  getProgramacion(corrPe: number, semestre?: number, codPeriodo?: string): Observable<ProgramacionHorario[]> {
    let params = new HttpParams().set('corr_pe', corrPe);
    if (semestre) params = params.set('semestre', semestre);
    if (codPeriodo) params = params.set('cod_periodo', codPeriodo);
    return this.http.get<ProgramacionHorario[]>(`${this.apiUrl}/programacion/`, { params });
  }

  getHorarios(corrPe: number, semestre?: number, codPeriodo?: string): Observable<HorarioDisponible[]> {
    let params = new HttpParams().set('corr_pe', corrPe);
    if (semestre) params = params.set('semestre', semestre);
    if (codPeriodo) params = params.set('cod_periodo', codPeriodo);
    return this.http.get<HorarioDisponible[]>(`${this.apiUrl}/horarios/`, { params });
  }

  crearSesion(sesion: SesionPayload): Observable<Mensaje> {
    return this.http.post<Mensaje>(`${this.apiUrl}/sesiones/`, sesion);
  }

  editarSesion(original: SesionLocator, sesion: SesionPayload): Observable<Mensaje> {
    return this.http.put<Mensaje>(`${this.apiUrl}/sesiones/`, { original, sesion });
  }

  getEstudiantes(buscar?: string): Observable<Estudiante[]> {
    let params = new HttpParams();
    if (buscar?.trim()) params = params.set('buscar', buscar.trim());
    return this.http.get<Estudiante[]>(`${this.apiUrl}/estudiantes/`, { params });
  }

  crearEstudiante(datos: EstudiantePayload): Observable<Estudiante> {
    return this.http.post<Estudiante>(`${this.apiUrl}/estudiantes/`, datos);
  }

  editarEstudiante(codigo: string, datos: Omit<EstudiantePayload, 'cod_estudiante'>): Observable<Estudiante> {
    return this.http.put<Estudiante>(
      `${this.apiUrl}/estudiantes/${encodeURIComponent(codigo)}`, datos
    );
  }

  eliminarEstudiante(codigo: string): Observable<Mensaje> {
    return this.http.delete<Mensaje>(
      `${this.apiUrl}/estudiantes/${encodeURIComponent(codigo)}`
    );
  }

  getOfertasEstudiante(codigo: string, periodo: string): Observable<OfertaCurso[]> {
    return this.http.get<OfertaCurso[]>(
      `${this.apiUrl}/estudiantes/${encodeURIComponent(codigo)}/ofertas`,
      { params: new HttpParams().set('cod_periodo', periodo) }
    );
  }

  getMatriculasEstudiante(codigo: string): Observable<MatriculaResumen[]> {
    return this.http.get<MatriculaResumen[]>(
      `${this.apiUrl}/estudiantes/${encodeURIComponent(codigo)}/matriculas`
    );
  }

  crearMatricula(codigo: string, periodo: string, ofertas: number[]): Observable<MatriculaResumen> {
    return this.http.post<MatriculaResumen>(`${this.apiUrl}/matriculas/`, {
      cod_estudiante: codigo, cod_periodo: periodo, ofertas
    });
  }

  registrarResultado(
    idMatricula: number, idOferta: number, detalle: MatriculaDetalle
  ): Observable<Mensaje> {
    return this.http.put<Mensaje>(
      `${this.apiUrl}/matriculas/${idMatricula}/ofertas/${idOferta}/resultado`,
      {
        nota_practicas: detalle.nota_practicas ?? null,
        nota_parcial: detalle.nota_parcial ?? null,
        nota_examen_final: detalle.nota_examen_final ?? null,
        nota_final: detalle.nota_final ?? null,
        resultado: detalle.resultado
      }
    );
  }

  abrirSeccion(datos: OfertaSeccionPayload): Observable<Mensaje> {
    return this.http.post<Mensaje>(`${this.apiUrl}/ofertas/secciones`, datos);
  }

  getOfertasAdministracion(periodo: string, corrPe: number, semestre?: number): Observable<OfertaAdministracion[]> {
    let params = new HttpParams().set('cod_periodo', periodo).set('corr_pe', corrPe);
    if (semestre) params = params.set('semestre', semestre);
    return this.http.get<OfertaAdministracion[]>(`${this.apiUrl}/ofertas/`, { params });
  }

  asignarDocente(idOferta: number, codDocente?: string): Observable<Mensaje> {
    return this.http.put<Mensaje>(`${this.apiUrl}/ofertas/${idOferta}/docente`, { cod_docente: codDocente || null });
  }

  guardarProgramacionCurso(datos: ProgramacionCursoPayload): Observable<Mensaje> {
    return this.http.put<Mensaje>(`${this.apiUrl}/horarios/cursos`, datos);
  }

  registrarResultadosLote(idMatricula: number, detalles: MatriculaDetalle[]): Observable<Mensaje> {
    return this.http.put<Mensaje>(
      `${this.apiUrl}/matriculas/${idMatricula}/resultados`,
      { resultados: detalles.map(item => ({
        id_oferta: item.id_oferta,
        nota_practicas: item.nota_practicas ?? null,
        nota_parcial: item.nota_parcial ?? null,
        nota_examen_final: item.nota_examen_final ?? null,
        nota_final: item.nota_final ?? null,
        resultado: item.resultado
      })) }
    );
  }

  getMiEstudiante(): Observable<Estudiante> {
    return this.http.get<Estudiante>(`${this.apiUrl}/estudiantes/me`);
  }

  getPrematricula(codigo: string): Observable<Prematricula> {
    return this.http.get<Prematricula>(`${this.apiUrl}/estudiantes/${encodeURIComponent(codigo)}/prematricula`);
  }

  guardarPrematricula(codigo: string, datos: Prematricula): Observable<Mensaje> {
    return this.http.put<Mensaje>(`${this.apiUrl}/estudiantes/${encodeURIComponent(codigo)}/prematricula`, datos);
  }

  getUsuarios(): Observable<UsuarioAdministracion[]> {
    return this.http.get<UsuarioAdministracion[]>(`${this.apiUrl}/usuarios/`);
  }

  crearUsuario(datos: UsuarioPayload): Observable<UsuarioAdministracion> {
    return this.http.post<UsuarioAdministracion>(`${this.apiUrl}/usuarios/`, datos);
  }

  editarUsuario(id: number, datos: UsuarioPayload): Observable<UsuarioAdministracion> {
    return this.http.put<UsuarioAdministracion>(`${this.apiUrl}/usuarios/${id}`, datos);
  }

  eliminarUsuario(id: number): Observable<Mensaje> {
    return this.http.delete<Mensaje>(`${this.apiUrl}/usuarios/${id}`);
  }

  getPerfiles(): Observable<PerfilAdministracion[]> {
    return this.http.get<PerfilAdministracion[]>(`${this.apiUrl}/perfiles/`);
  }

  editarPerfil(id: number, nombre: string, permisos: string[]): Observable<PerfilAdministracion> {
    return this.http.put<PerfilAdministracion>(`${this.apiUrl}/perfiles/${id}`, { nombre, permisos });
  }

  crearPerfil(codigo: string, nombre: string, permisos: string[]): Observable<PerfilAdministracion> {
    return this.http.post<PerfilAdministracion>(`${this.apiUrl}/perfiles/`, { codigo, nombre, permisos });
  }

  eliminarPerfil(id: number): Observable<Mensaje> {
    return this.http.delete<Mensaje>(`${this.apiUrl}/perfiles/${id}`);
  }
}
