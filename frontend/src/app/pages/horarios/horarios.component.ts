import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ApiService, Curso, Docente, HorarioDisponible, OfertaAdministracion, PeriodoAcademico, PlanEstudio, ProgramacionHorario } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({ selector: 'app-horarios', templateUrl: './horarios.component.html', styleUrls: ['./horarios.component.css'] })
export class HorariosComponent implements OnInit {
  planes: PlanEstudio[] = []; periodos: PeriodoAcademico[] = []; semestres: number[] = [];
  ofertas: OfertaAdministracion[] = []; cursos: Curso[] = []; sesiones: ProgramacionHorario[] = []; horarios: HorarioDisponible[] = []; docentes: Docente[] = [];
  plan = 0; semestre = 0; periodo = ''; oferta?: OfertaAdministracion;
  aula = ''; teoriaDia = 'LUNES'; teoriaInicio = '08:00'; practicaDia = 'MARTES'; practicaInicio = '08:00';
  nuevaSeccion = 'D'; capacidad = 35; cursoSeccion = ''; mensaje = ''; error = '';
  readonly dias = ['LUNES','MARTES','MIERCOLES','JUEVES','VIERNES','SABADO'];
  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit(): void {
    this.api.getDocentes().subscribe(data => this.docentes = data);
    this.api.getPeriodos().subscribe(data => { this.periodos = data; this.periodo = data.find(p => p.activo)?.cod_periodo || data[0]?.cod_periodo || ''; this.cargar(); });
    this.api.getPlanes().subscribe(data => { this.planes = data; this.plan = data.find(p => p.vigente)?.corr_pe || data[0]?.corr_pe || 0; this.cambiarPlan(); });
  }
  cambiarPlan(): void { this.semestre = 0; this.ofertas = []; this.api.getSemestres(this.plan).subscribe(data => this.semestres = data); }
  cargar(): void {
    if (!this.plan || !this.semestre || !this.periodo) return;
    this.oferta = undefined;
    this.cursoSeccion = '';
    this.nuevaSeccion = this.periodos.find(p => p.cod_periodo === this.periodo)?.tipo_periodo === 'VERANO' ? 'A' : 'D';
    this.api.getCursos(this.plan, this.semestre).subscribe(data => this.cursos = data);
    this.api.getHorarios(this.plan, this.semestre, this.periodo).subscribe(data => this.horarios = data);
    this.api.getProgramacion(this.plan, this.semestre, this.periodo).subscribe(data => this.sesiones = data);
    this.api.getOfertasAdministracion(this.periodo, this.plan, this.semestre).subscribe({ next: data => this.ofertas = data, error: e => this.mostrarError(e) });
  }
  seleccionar(oferta: OfertaAdministracion): void {
    this.oferta = oferta; this.aula = `S${String(oferta.semestre).padStart(2,'0')}-${oferta.cod_seccion}`;
    const existentes = this.sesiones.filter(s => s.cod_curso === oferta.cod_curso && s.cod_seccion === oferta.cod_seccion);
    const t = existentes.find(s => s.tipo_sesion === 'T'), p = existentes.find(s => s.tipo_sesion === 'P');
    const inicio = this.inicioTurno(oferta.semestre, oferta.cod_seccion);
    this.teoriaDia = t?.dia_semana || 'LUNES'; this.teoriaInicio = t?.hora_inicio.slice(0,5) || inicio;
    this.practicaDia = p?.dia_semana || 'MARTES'; this.practicaInicio = p?.hora_inicio.slice(0,5) || inicio;
    this.aula = t?.aula || p?.aula || this.aula;
  }
  guardar(): void {
    if (!this.oferta || !this.horarios.length) return;
    this.limpiar();
    this.api.guardarProgramacionCurso({
      id_horario: this.horarios[0].id_horario, semestre_corr: this.semestre, corr_pe: this.plan,
      cod_curso: this.oferta.cod_curso, cod_seccion: this.oferta.cod_seccion, aula: this.aula,
      teoria: this.oferta.ht ? { dia_semana: this.teoriaDia, hora_inicio: this.teoriaInicio } : undefined,
      practica: this.oferta.hp ? { dia_semana: this.practicaDia, hora_inicio: this.practicaInicio } : undefined
    }).subscribe({ next: r => { this.mensaje = r.mensaje; this.cargar(); }, error: e => this.mostrarError(e) });
  }
  asignarDocente(oferta: OfertaAdministracion, codigo: string): void {
    this.api.asignarDocente(oferta.id_oferta, codigo || undefined).subscribe({ next: r => { this.mensaje = r.mensaje; this.cargar(); }, error: e => this.mostrarError(e) });
  }
  abrirSeccion(): void {
    this.api.abrirSeccion({ cod_periodo: this.periodo, corr_pe: this.plan, cod_curso: this.cursoSeccion, cod_seccion: this.nuevaSeccion, vacantes: Number(this.capacidad) }).subscribe({
      next: r => { this.mensaje = r.mensaje; this.cargar(); }, error: e => this.mostrarError(e)
    });
  }
  fin(inicio: string, horas: number): string {
    const [h,m] = inicio.split(':').map(Number), total = h * 60 + m + horas * 50;
    return `${String(Math.floor(total / 60)).padStart(2,'0')}:${String(total % 60).padStart(2,'0')}`;
  }
  inicioTurno(ciclo: number, seccion: string): string {
    if (ciclo <= 2 || (ciclo === 3 && seccion !== 'C')) return '08:00';
    if (ciclo <= 5 || (ciclo === 6 && seccion === 'A') || ciclo === 3) return '13:00';
    return '17:10';
  }
  romano(n: number): string { return ['I','II','III','IV','V','VI','VII','VIII','IX','X'][n-1]; }
  sesionesOferta(o: OfertaAdministracion): ProgramacionHorario[] { return this.sesiones.filter(s => s.cod_curso === o.cod_curso && s.cod_seccion === o.cod_seccion); }
  private limpiar(): void { this.mensaje = ''; this.error = ''; }
  private mostrarError(e: HttpErrorResponse): void { this.mensaje = ''; this.error = typeof e.error?.detail === 'string' ? e.error.detail : 'No se pudo completar la operación.'; }
}
