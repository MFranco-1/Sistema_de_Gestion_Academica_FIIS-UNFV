import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { jsPDF } from 'jspdf';
import { ApiService, BloqueHorario, Estudiante, MatriculaAccesoEstado, MatriculaResumen, OfertaCurso, PeriodoAcademico, RankingCiclo, RankingEstudiante } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({ selector: 'app-matricula', templateUrl: './matricula.component.html', styleUrls: ['./matricula.component.css'] })
export class MatriculaComponent implements OnInit {
  estudiante?: Estudiante;
  private periodosBase: PeriodoAcademico[] = [];
  private historialCargado = false;
  periodos: PeriodoAcademico[] = [];
  ofertas: OfertaCurso[] = [];
  matriculas: MatriculaResumen[] = [];
  seleccionadas = new Set<number>();
  periodoSeleccionado = '';
  seccionFiltro = 'TODAS';
  mensaje = '';
  error = '';
  cargando = true;
  confirmando = false;
  ultimaMatricula?: MatriculaResumen;
  ranking?: RankingCiclo;
  accesoMatricula?: MatriculaAccesoEstado;
  fotoPerfil = '';
  readonly diasHorario = ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES', 'SABADO'];

  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit(): void {
    this.cargarFicha();
    this.api.getPeriodos().subscribe({
      next: data => {
        this.periodosBase = data;
        this.actualizarPeriodosMatricula();
      },
      error: error => this.mostrarError(error)
    });
  }

  cargarFicha(): void {
    this.api.getMiEstudiante().subscribe({
      next: estudiante => {
        this.estudiante = estudiante;
        this.fotoPerfil = localStorage.getItem(`fiis_foto_${estudiante.cod_estudiante}`) || '';
        this.cargando = false;
        this.historialCargado = false;
        this.api.getMatriculasEstudiante(estudiante.cod_estudiante).subscribe({
          next: matriculas => {
            this.matriculas = matriculas;
            this.historialCargado = true;
            this.actualizarPeriodosMatricula();
          },
          error: () => {
            this.matriculas = [];
            this.historialCargado = true;
            this.actualizarPeriodosMatricula();
          }
        });
      },
      error: error => { this.cargando = false; this.mostrarError(error); }
    });
  }

  cargarOfertas(): void {
    if (!this.estudiante || !this.periodoSeleccionado) return;
    this.seleccionadas.clear();
    this.cargarEstadoMatricula();
    this.api.getOfertasEstudiante(this.estudiante.cod_estudiante, this.periodoSeleccionado).subscribe({
      next: data => {
        this.ofertas = data;
        const secciones = this.seccionesDisponibles;
        if (this.seccionFiltro !== 'TODAS' && !secciones.includes(this.seccionFiltro)) this.seccionFiltro = 'TODAS';
        this.api.getPrematricula(this.estudiante!.cod_estudiante).subscribe(guardada => {
          if (guardada.cod_periodo === this.periodoSeleccionado) {
            const validas = new Set(data.map(item => item.id_oferta));
            this.seleccionadas = new Set(guardada.ofertas.filter(id => validas.has(id)));
          }
        });
      },
      error: error => this.mostrarError(error)
    });
  }

  private actualizarPeriodosMatricula(): void {
    if (!this.estudiante || !this.periodosBase.length || !this.historialCargado) return;
    const tipoCorrespondiente = this.estudiante.ciclo_actual % 2 ? 'I' : 'II';
    const activo = this.periodosBase.find(periodo => periodo.activo);
    const matriculaActiva = activo
      ? this.matriculas.find(matricula => matricula.cod_periodo === activo.cod_periodo)
      : undefined;
    const regulares = this.periodosBase
      .filter(periodo => periodo.tipo_periodo === tipoCorrespondiente)
      .sort((a, b) => a.fecha_inicio.localeCompare(b.fecha_inicio));
    const periodoActivoCompatible = matriculaActiva?.estado === 'CERRADA'
      ? undefined
      : regulares.find(periodo => periodo.activo);
    const correspondiente = periodoActivoCompatible
      || (activo ? regulares.find(periodo => periodo.fecha_inicio > activo.fecha_inicio) : undefined)
      || regulares.find(periodo => periodo.fecha_fin >= new Date().toISOString().slice(0, 10))
      || regulares[regulares.length - 1];
    const veranoActivo = this.periodosBase.find(periodo => periodo.activo && periodo.tipo_periodo === 'VERANO');
    this.periodos = [veranoActivo, correspondiente]
      .filter((periodo, indice, lista): periodo is PeriodoAcademico =>
        !!periodo && lista.findIndex(item => item?.cod_periodo === periodo.cod_periodo) === indice
      );
    if (!this.periodos.some(periodo => periodo.cod_periodo === this.periodoSeleccionado)) {
      this.periodoSeleccionado = this.periodos[0]?.cod_periodo || '';
    }
    this.cargarOfertas();
  }

  private cargarEstadoMatricula(): void {
    this.ranking = undefined;
    this.accesoMatricula = undefined;
    this.api.getMiRanking(this.periodoSeleccionado).subscribe({
      next: ranking => this.ranking = ranking,
      error: () => this.ranking = undefined
    });
    this.api.getMiAccesoMatricula(this.periodoSeleccionado).subscribe({
      next: acceso => this.accesoMatricula = acceso,
      error: error => this.mostrarError(error)
    });
  }

  alternarOferta(id: number, seleccionada: boolean): void {
    if (seleccionada) {
      const elegida = this.ofertas.find(item => item.id_oferta === id);
      if (elegida) this.ofertas.filter(item => item.cod_curso === elegida.cod_curso).forEach(item => this.seleccionadas.delete(item.id_oferta));
      this.seleccionadas.add(id);
    } else this.seleccionadas.delete(id);
  }

  seleccionarSeccion(seccion: string): void {
    this.seccionFiltro = seccion;
  }

  guardarPrematricula(): void {
    if (!this.estudiante) return;
    this.mensaje = ''; this.error = '';
    this.api.guardarPrematricula(this.estudiante.cod_estudiante, { cod_periodo: this.periodoSeleccionado, ofertas: [...this.seleccionadas] }).subscribe({
      next: data => this.mensaje = data.mensaje,
      error: error => this.mostrarError(error)
    });
  }

  bloquesDia(dia: string): { oferta: OfertaCurso; bloque: BloqueHorario }[] {
    const resultado: { oferta: OfertaCurso; bloque: BloqueHorario }[] = [];
    this.ofertas.filter(o => this.seleccionadas.has(o.id_oferta)).forEach(oferta => oferta.horarios.filter(b => b.dia_semana === dia).forEach(bloque => resultado.push({ oferta, bloque })));
    return resultado.sort((a, b) => a.bloque.hora_inicio.localeCompare(b.bloque.hora_inicio));
  }

  get crucePrematricula(): string {
    const bloques = this.diasHorario.flatMap(dia => this.bloquesDia(dia));
    const minutos = (v: string) => { const [h, m] = v.slice(0, 5).split(':').map(Number); return h * 60 + m; };
    for (let i = 0; i < bloques.length; i++) for (let j = i + 1; j < bloques.length; j++) {
      const a = bloques[i], b = bloques[j];
      if (a.bloque.dia_semana === b.bloque.dia_semana && a.oferta.cod_curso !== b.oferta.cod_curso && minutos(a.bloque.hora_inicio) < minutos(b.bloque.hora_fin) && minutos(a.bloque.hora_fin) > minutos(b.bloque.hora_inicio)) return `${a.oferta.cod_curso} se cruza con ${b.oferta.cod_curso} el ${a.bloque.dia_semana.toLowerCase()}.`;
    }
    return '';
  }

  abrirConfirmacion(): void {
    if (!this.seleccionadas.size || this.crucePrematricula || !this.puedeRegistrar) return;
    this.confirmando = true;
  }

  registrarMatricula(): void {
    if (!this.estudiante || !this.seleccionadas.size || !this.puedeRegistrar) return;
    this.mensaje = ''; this.error = '';
    this.api.crearMatricula(this.estudiante.cod_estudiante, this.periodoSeleccionado, [...this.seleccionadas]).subscribe({
      next: matricula => {
        this.ultimaMatricula = matricula;
        this.confirmando = false;
        this.mensaje = 'Matrícula registrada correctamente. Ya puede descargar su constancia.';
        this.cargarFicha();
      },
      error: error => { this.confirmando = false; this.mostrarError(error); }
    });
  }

  descargarConstancia(): void {
    const matricula = this.ultimaMatricula;
    const estudiante = this.estudiante;
    if (!matricula || !estudiante) return;
    const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
    const maroon: [number, number, number] = [132, 29, 42];
    const gold: [number, number, number] = [199, 146, 38];
    pdf.setDrawColor(...maroon);
    pdf.setLineWidth(1.2);
    pdf.line(12, 13, 285, 13);
    pdf.setTextColor(...maroon);
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(14);
    pdf.text('UNIVERSIDAD NACIONAL FEDERICO VILLARREAL', 12, 22);
    pdf.setFontSize(11);
    pdf.text('FACULTAD DE INGENIERÍA INDUSTRIAL Y DE SISTEMAS', 12, 28);
    pdf.setTextColor(40, 40, 40);
    pdf.setFontSize(9);
    pdf.text('ESCUELA PROFESIONAL DE INGENIERÍA DE SISTEMAS', 12, 33);
    pdf.setFontSize(17);
    pdf.text(`CONSTANCIA DE MATRÍCULA ${matricula.cod_periodo}`, 148.5, 43, { align: 'center' });
    pdf.setFontSize(9);
    pdf.setFont('helvetica', 'normal');
    pdf.text(`Alumno: ${estudiante.apellidos_nombres}`, 12, 51);
    pdf.text(`Código: ${estudiante.cod_estudiante}`, 12, 56);
    pdf.text(`Plan: ${estudiante.den_plan}`, 112, 51);
    pdf.text(`Ciclo: ${this.semestreRomano(matricula.ciclo_matricula)}`, 112, 56);
    pdf.text(`Fecha: ${new Date(matricula.fecha_matricula + 'T00:00:00').toLocaleDateString('es-PE')}`, 235, 51);
    pdf.text(`Matrícula N.° ${matricula.id_matricula}`, 235, 56);
    const columnas = [12, 22, 47, 116, 132, 224, 251, 285];
    const encabezados = ['N.°', 'CÓDIGO', 'ASIGNATURA', 'SEC.', 'DOCENTE', 'CRÉDITOS', 'CICLO'];
    let y = 64;
    pdf.setFillColor(...maroon);
    pdf.rect(12, y, 273, 8, 'F');
    pdf.setTextColor(255, 255, 255);
    pdf.setFont('helvetica', 'bold');
    encabezados.forEach((texto, indice) => pdf.text(texto, columnas[indice] + 1.5, y + 5.3));
    y += 8;
    pdf.setTextColor(35, 35, 35);
    pdf.setFont('helvetica', 'normal');
    matricula.detalles.forEach((detalle, indice) => {
      const alto = 9;
      if (y + alto > 190) { pdf.addPage('a4', 'landscape'); y = 18; }
      if (indice % 2) { pdf.setFillColor(247, 244, 242); pdf.rect(12, y, 273, alto, 'F'); }
      pdf.setDrawColor(220, 214, 210);
      pdf.line(12, y + alto, 285, y + alto);
      const valores = [String(indice + 1), detalle.cod_curso, detalle.den_curso, detalle.cod_seccion, detalle.docente_nombre, String(detalle.cred), this.semestreRomano(detalle.semestre)];
      valores.forEach((texto, col) => {
        const ancho = columnas[col + 1] - columnas[col] - 3;
        pdf.text(pdf.splitTextToSize(texto, ancho).slice(0, 2), columnas[col] + 1.5, y + 4);
      });
      y += alto;
    });
    pdf.setDrawColor(...gold);
    pdf.setLineWidth(.8);
    pdf.line(12, y + 4, 285, y + 4);
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(11);
    pdf.setTextColor(...maroon);
    pdf.text(`TOTAL DE CRÉDITOS: ${matricula.total_creditos}`, 285, y + 11, { align: 'right' });
    pdf.setTextColor(90, 90, 90);
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(8);
    pdf.text('Documento generado por el Sistema de Gestión Académica FIIS–UNFV.', 12, 200);
    pdf.save(`constancia-matricula-${matricula.cod_periodo}-${estudiante.cod_estudiante}.pdf`);
  }

  semestreRomano(numero: number): string { return ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'][numero - 1]; }
  get iniciales(): string {
    return (this.estudiante?.apellidos_nombres || '').split(/[ ,]+/).filter(Boolean).slice(0, 2).map(parte => parte[0]).join('').toUpperCase();
  }
  seleccionarFoto(event: Event): void {
    const archivo = (event.target as HTMLInputElement).files?.[0];
    if (!archivo || !archivo.type.startsWith('image/')) return;
    if (archivo.size > 1024 * 1024) { this.error = 'La foto debe pesar como máximo 1 MB.'; return; }
    const lector = new FileReader();
    lector.onload = () => {
      this.fotoPerfil = String(lector.result);
      if (this.estudiante) localStorage.setItem(`fiis_foto_${this.estudiante.cod_estudiante}`, this.fotoPerfil);
    };
    lector.readAsDataURL(archivo);
  }
  get creditosSeleccionados(): number {
    return this.ofertasSeleccionadas.reduce((total, item) => total + item.cred, 0);
  }
  get ofertasSeleccionadas(): OfertaCurso[] {
    return this.ofertas.filter(item => this.seleccionadas.has(item.id_oferta));
  }
  get miRanking(): RankingEstudiante | undefined {
    return this.ranking?.estudiantes.find(item => item.cod_estudiante === this.estudiante?.cod_estudiante);
  }
  get puedeRegistrar(): boolean {
    return !!this.accesoMatricula?.habilitado;
  }
  get seccionesDisponibles(): string[] {
    return [...new Set(this.ofertas.map(item => item.cod_seccion))].sort((a, b) => a.localeCompare(b));
  }
  get ofertasFiltradas(): OfertaCurso[] {
    return this.ofertas
      .filter(item => this.seccionFiltro === 'TODAS' || item.cod_seccion === this.seccionFiltro)
      .sort((a, b) => a.semestre - b.semestre || a.cod_curso.localeCompare(b.cod_curso) || a.cod_seccion.localeCompare(b.cod_seccion));
  }
  cantidadSeccion(seccion: string): number {
    return this.ofertas.filter(item => item.cod_seccion === seccion).length;
  }
  get totalOfertasDisponibles(): number {
    return this.ofertas.length;
  }
  private mostrarError(error: HttpErrorResponse): void {
    this.mensaje = '';
    const detalle = error.error?.detail;
    this.error = typeof detalle === 'string' ? detalle : 'No se pudo completar la operación.';
  }
}
