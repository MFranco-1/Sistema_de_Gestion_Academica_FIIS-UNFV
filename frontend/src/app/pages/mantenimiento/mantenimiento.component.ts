import { HttpErrorResponse } from '@angular/common/http';
import { AfterViewInit, Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import {
  ApiService, Curso, CursoDetalle, CursoPayload, HorarioDisponible, PeriodoAcademico,
  PlanEstudio, ProgramacionHorario, SesionLocator, SesionPayload, Estudiante,
  EstudiantePayload
} from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-mantenimiento',
  templateUrl: './mantenimiento.component.html',
  styleUrls: ['./mantenimiento.component.css']
})
export class MantenimientoComponent implements OnInit, AfterViewInit {
  planes: PlanEstudio[] = [];
  semestres: number[] = [];
  cursos: Curso[] = [];
  periodos: PeriodoAcademico[] = [];
  horarios: HorarioDisponible[] = [];
  sesiones: ProgramacionHorario[] = [];
  selectedPlan?: number;
  selectedSemester?: number;
  selectedPeriodo?: string;
  cursoSeleccionado?: Curso;
  detalle?: CursoDetalle;
  prerequisitoCodigo = '';
  editandoCodigo?: string;
  sesionOriginal?: SesionLocator;
  mensaje = '';
  error = '';
  estudiantes: Estudiante[] = [];
  editandoEstudiante = '';
  estudianteForm: EstudiantePayload = this.nuevoEstudiante();
  nuevaSeccion = 'D';
  capacidadSeccion = 35;
  cursoNuevaSeccion = '';

  cursoForm: CursoPayload = this.nuevoCurso();
  sesionForm: SesionPayload = this.nuevaSesion();

  constructor(private api: ApiService, public auth: AuthService, private route: ActivatedRoute) {}

  ngAfterViewInit(): void {
    this.route.fragment.subscribe(fragment => {
      if (fragment) {
        setTimeout(() => document.getElementById(fragment)?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
      }
    });
  }

  ngOnInit(): void {
    if (this.auth.puede('GESTION_ESTUDIANTES')) this.cargarEstudiantes();
    this.api.getPeriodos().subscribe(data => {
      this.periodos = data;
      this.selectedPeriodo = data.find(p => p.activo)?.cod_periodo ?? data[0]?.cod_periodo;
    });
    this.api.getPlanes().subscribe({
      next: data => {
        this.planes = data;
        this.selectedPlan = data.find(p => p.vigente)?.corr_pe ?? data[0]?.corr_pe;
        this.cambiarPlan();
      },
      error: error => this.mostrarError(error)
    });
  }

  cambiarPlan(): void {
    this.selectedSemester = undefined;
    this.semestres = [];
    this.cursos = [];
    this.sesiones = [];
    this.horarios = [];
    this.cursoSeleccionado = undefined;
    this.detalle = undefined;
    this.cancelarCurso();
    this.cancelarSesion();
    if (!this.selectedPlan) return;
    this.cursoForm.corr_pe = Number(this.selectedPlan);
    this.sesionForm.corr_pe = Number(this.selectedPlan);
    this.api.getSemestres(Number(this.selectedPlan)).subscribe({
      next: data => this.semestres = data,
      error: error => this.mostrarError(error)
    });
  }

  cambiarSemestre(): void {
    this.cursoSeleccionado = undefined;
    this.detalle = undefined;
    this.cancelarSesion();
    if (!this.selectedPlan || !this.selectedSemester) {
      this.cursos = [];
      this.sesiones = [];
      return;
    }
    this.cursoForm.semestre = Number(this.selectedSemester);
    this.sesionForm.semestre_corr = Number(this.selectedSemester);
    this.cargarCursos();
    this.cargarHorario();
  }

  cargarCursos(): void {
    if (!this.selectedPlan || !this.selectedSemester) return;
    this.api.getCursos(Number(this.selectedPlan), Number(this.selectedSemester)).subscribe({
      next: data => this.cursos = data,
      error: error => this.mostrarError(error)
    });
  }

  cargarHorario(): void {
    if (!this.selectedPlan || !this.selectedSemester) return;
    const plan = Number(this.selectedPlan);
    const semestre = Number(this.selectedSemester);
    this.api.getHorarios(plan, semestre, this.selectedPeriodo).subscribe({
      next: data => {
        this.horarios = data;
        if (!this.sesionOriginal) this.sesionForm.id_horario = data[0]?.id_horario ?? 0;
      },
      error: error => this.mostrarError(error)
    });
    this.api.getProgramacion(plan, semestre, this.selectedPeriodo).subscribe({
      next: data => this.sesiones = data,
      error: error => this.mostrarError(error)
    });
  }

  guardarCurso(): void {
    this.limpiarMensajes();
    if (!this.selectedPlan) return;
    this.cursoForm.corr_pe = Number(this.selectedPlan);
    const operacion = this.editandoCodigo
      ? this.api.editarCurso(Number(this.selectedPlan), this.editandoCodigo, {
          den_curso: this.cursoForm.den_curso,
          semestre: Number(this.cursoForm.semestre),
          ht: Number(this.cursoForm.ht), hp: Number(this.cursoForm.hp),
          cred: Number(this.cursoForm.cred), tipo_curso: this.cursoForm.tipo_curso
        })
      : this.api.crearCurso({
          ...this.cursoForm,
          semestre: Number(this.cursoForm.semestre), ht: Number(this.cursoForm.ht),
          hp: Number(this.cursoForm.hp), cred: Number(this.cursoForm.cred)
        });
    operacion.subscribe({
      next: curso => {
        this.mensaje = this.editandoCodigo ? 'Curso actualizado correctamente.' : 'Curso registrado correctamente.';
        this.cancelarCurso();
        if (!this.semestres.includes(curso.semestre)) this.semestres = [...this.semestres, curso.semestre].sort((a, b) => a - b);
        this.selectedSemester = curso.semestre;
        this.cargarCursos();
      },
      error: error => this.mostrarError(error)
    });
  }

  editarCurso(curso: Curso): void {
    this.editandoCodigo = curso.cod_curso;
    this.cursoForm = {
      corr_pe: curso.corr_pe, cod_curso: curso.cod_curso, den_curso: curso.den_curso,
      semestre: curso.semestre, ht: curso.ht, hp: curso.hp, cred: curso.cred,
      tipo_curso: curso.tipo_curso
    };
    this.limpiarMensajes();
  }

  eliminarCurso(curso: Curso): void {
    if (!window.confirm(`¿Eliminar el curso ${curso.cod_curso}?`)) return;
    this.api.eliminarCurso(curso.corr_pe, curso.cod_curso).subscribe({
      next: data => {
        this.mensaje = data.mensaje;
        this.cargarCursos();
        if (this.cursoSeleccionado?.cod_curso === curso.cod_curso) {
          this.cursoSeleccionado = undefined;
          this.detalle = undefined;
        }
      },
      error: error => this.mostrarError(error)
    });
  }

  cancelarCurso(): void {
    this.editandoCodigo = undefined;
    this.cursoForm = this.nuevoCurso();
    if (this.selectedPlan) this.cursoForm.corr_pe = Number(this.selectedPlan);
    if (this.selectedSemester) this.cursoForm.semestre = Number(this.selectedSemester);
  }

  seleccionarCurso(curso: Curso): void {
    this.cursoSeleccionado = curso;
    this.prerequisitoCodigo = '';
    this.cargarDetalle();
  }

  get candidatosPrerequisito(): Curso[] {
    if (!this.cursoSeleccionado || !this.selectedPlan) return [];
    return this.todosCursosPlan.filter(c => c.semestre < this.cursoSeleccionado!.semestre);
  }

  todosCursosPlan: Curso[] = [];

  cargarDetalle(): void {
    if (!this.cursoSeleccionado || !this.selectedPlan) return;
    this.api.getCursoDetalle(Number(this.selectedPlan), this.cursoSeleccionado.cod_curso).subscribe({
      next: data => this.detalle = data,
      error: error => this.mostrarError(error)
    });
    this.api.getCursos(Number(this.selectedPlan)).subscribe(data => this.todosCursosPlan = data);
  }

  agregarPrerequisito(): void {
    if (!this.cursoSeleccionado || !this.prerequisitoCodigo || !this.selectedPlan) return;
    this.api.agregarPrerequisito({
      corr_pe: Number(this.selectedPlan), cod_curso: this.cursoSeleccionado.cod_curso,
      cod_curso_prerequisito: this.prerequisitoCodigo
    }).subscribe({
      next: data => { this.mensaje = data.mensaje; this.cargarDetalle(); this.cargarCursos(); },
      error: error => this.mostrarError(error)
    });
  }

  retirarPrerequisito(codigo: string): void {
    if (!this.cursoSeleccionado || !this.selectedPlan) return;
    this.api.retirarPrerequisito(
      Number(this.selectedPlan), this.cursoSeleccionado.cod_curso, codigo
    ).subscribe({
      next: data => { this.mensaje = data.mensaje; this.cargarDetalle(); this.cargarCursos(); },
      error: error => this.mostrarError(error)
    });
  }

  guardarSesion(): void {
    this.limpiarMensajes();
    if (!this.selectedPlan || !this.selectedSemester || !this.sesionForm.id_horario) {
      this.error = 'Seleccione una malla, semestre y horario disponibles.';
      return;
    }
    const sesion: SesionPayload = {
      ...this.sesionForm,
      corr_pe: Number(this.selectedPlan), semestre_corr: Number(this.selectedSemester),
      id_horario: Number(this.sesionForm.id_horario)
    };
    const operacion = this.sesionOriginal
      ? this.api.editarSesion(this.sesionOriginal, sesion)
      : this.api.crearSesion(sesion);
    operacion.subscribe({
      next: data => { this.mensaje = data.mensaje; this.cancelarSesion(); this.cargarHorario(); },
      error: error => this.mostrarError(error)
    });
  }

  abrirSeccion(): void {
    if (!this.selectedPlan || !this.selectedPeriodo || !this.cursoNuevaSeccion) return;
    this.limpiarMensajes();
    this.api.abrirSeccion({
      cod_periodo: this.selectedPeriodo, corr_pe: Number(this.selectedPlan),
      cod_curso: this.cursoNuevaSeccion, cod_seccion: this.nuevaSeccion,
      vacantes: Number(this.capacidadSeccion)
    }).subscribe({
      next: data => { this.mensaje = data.mensaje; this.nuevaSeccion = 'D'; },
      error: error => this.mostrarError(error)
    });
  }

  get cursoSesion(): Curso | undefined {
    return this.cursos.find(curso => curso.cod_curso === this.sesionForm.cod_curso);
  }

  get horasMallaSesion(): number {
    if (!this.cursoSesion) return 0;
    return this.sesionForm.tipo_sesion === 'T' ? this.cursoSesion.ht : this.cursoSesion.hp;
  }

  get horasAsignadasSesion(): number {
    return this.sesiones.filter(item =>
      item.cod_curso === this.sesionForm.cod_curso &&
      item.cod_seccion === this.sesionForm.cod_seccion &&
      item.tipo_sesion === this.sesionForm.tipo_sesion &&
      (!this.sesionOriginal || !(item.dia_semana === this.sesionOriginal.dia_semana && item.hora_inicio === this.sesionOriginal.hora_inicio))
    ).reduce((total, item) => total + this.duracionAcademica(item.hora_inicio, item.hora_fin), 0);
  }

  get turnoSesion(): string {
    const ciclo = Number(this.selectedSemester || 0), seccion = this.sesionForm.cod_seccion.toUpperCase();
    if (ciclo <= 2 || (ciclo === 3 && seccion !== 'C')) return 'Mañana: 08:00 a 15:00';
    if (ciclo <= 5 || (ciclo === 6 && seccion === 'A') || ciclo === 3) return 'Tarde: 13:00 a 18:00';
    return 'Noche: 17:10 a 22:10 (6 bloques académicos)';
  }

  private duracionAcademica(inicio: string, fin: string): number {
    const minutos = (valor: string) => { const [h, m] = valor.slice(0, 5).split(':').map(Number); return h * 60 + m; };
    return (minutos(fin) - minutos(inicio)) / 50;
  }

  editarSesion(sesion: ProgramacionHorario): void {
    this.sesionOriginal = {
      id_horario: sesion.id_horario, semestre_corr: sesion.semestre_corr,
      cod_curso: sesion.cod_curso, cod_seccion: sesion.cod_seccion,
      tipo_sesion: sesion.tipo_sesion, dia_semana: sesion.dia_semana,
      hora_inicio: sesion.hora_inicio
    };
    this.sesionForm = {
      id_horario: sesion.id_horario, semestre_corr: sesion.semestre_corr,
      cod_curso: sesion.cod_curso, cod_seccion: sesion.cod_seccion,
      tipo_sesion: sesion.tipo_sesion, corr_pe: sesion.corr_pe,
      dia_semana: sesion.dia_semana, hora_inicio: sesion.hora_inicio.slice(0, 5),
      hora_fin: sesion.hora_fin.slice(0, 5), aula: sesion.aula
    };
    this.limpiarMensajes();
  }

  cancelarSesion(): void {
    this.sesionOriginal = undefined;
    this.sesionForm = this.nuevaSesion();
    if (this.selectedPlan) this.sesionForm.corr_pe = Number(this.selectedPlan);
    if (this.selectedSemester) this.sesionForm.semestre_corr = Number(this.selectedSemester);
    this.sesionForm.id_horario = this.horarios[0]?.id_horario ?? 0;
  }

  semestreRomano(numero: number): string {
    return ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'][numero - 1];
  }

  cargarEstudiantes(): void {
    this.api.getEstudiantes().subscribe({ next: data => this.estudiantes = data, error: error => this.mostrarError(error) });
  }

  guardarEstudiante(): void {
    this.limpiarMensajes();
    const operacion = this.editandoEstudiante
      ? this.api.editarEstudiante(this.editandoEstudiante, this.estudianteForm)
      : this.api.crearEstudiante(this.estudianteForm);
    operacion.subscribe({
      next: () => {
        this.mensaje = this.editandoEstudiante ? 'Estudiante actualizado correctamente.' : 'Estudiante y cuenta de acceso registrados correctamente.';
        this.cancelarEstudiante(); this.cargarEstudiantes();
      }, error: error => this.mostrarError(error)
    });
  }

  editarEstudiante(estudiante: Estudiante): void {
    this.editandoEstudiante = estudiante.cod_estudiante;
    this.estudianteForm = { cod_estudiante: estudiante.cod_estudiante, dni: estudiante.dni, apellidos_nombres: estudiante.apellidos_nombres, correo: estudiante.correo, cod_fac: estudiante.cod_fac, cod_esc: estudiante.cod_esc, corr_pe: estudiante.corr_pe, ciclo_actual: estudiante.ciclo_actual, estado: estudiante.estado };
  }

  eliminarEstudiante(estudiante: Estudiante): void {
    if (!confirm(`¿Eliminar al estudiante ${estudiante.cod_estudiante}?`)) return;
    this.api.eliminarEstudiante(estudiante.cod_estudiante).subscribe({ next: data => { this.mensaje = data.mensaje; this.cargarEstudiantes(); }, error: error => this.mostrarError(error) });
  }

  cancelarEstudiante(): void { this.editandoEstudiante = ''; this.estudianteForm = this.nuevoEstudiante(); }


  private nuevoCurso(): CursoPayload {
    return { corr_pe: 0, cod_curso: '', den_curso: '', semestre: 1, ht: 0, hp: 0, cred: 1, tipo_curso: 'OBLIGATORIO' };
  }

  private nuevaSesion(): SesionPayload {
    return { id_horario: 0, semestre_corr: 1, cod_curso: '', cod_seccion: 'A', tipo_sesion: 'T', corr_pe: 0, dia_semana: 'LUNES', hora_inicio: '08:00', hora_fin: '08:50', aula: '' };
  }

  private nuevoEstudiante(): EstudiantePayload {
    return { cod_estudiante: '', dni: '', apellidos_nombres: '', correo: '', cod_fac: 1, cod_esc: 1, corr_pe: 2, ciclo_actual: 1, estado: 'ACTIVO' };
  }

  private limpiarMensajes(): void { this.mensaje = ''; this.error = ''; }

  private mostrarError(error: HttpErrorResponse): void {
    this.mensaje = '';
    const detalle = error.error?.detail;
    this.error = typeof detalle === 'string' ? detalle : 'No se pudo completar la operación solicitada.';
  }
}
