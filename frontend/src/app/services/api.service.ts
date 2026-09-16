import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

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

@Injectable({ providedIn: 'root' })
export class ApiService {
  private apiUrl = 'http://localhost:8000';
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
}
