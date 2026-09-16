import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import {
  ApiService, Curso, CursoDetalle, PeriodoAcademico, PlanEstudio,
  ProgramacionHorario, ResumenSemestre
} from '../../services/api.service';

@Component({
  selector: 'app-catalog',
  templateUrl: './catalog.component.html',
  styleUrls: ['./catalog.component.css']
})
export class CatalogComponent implements OnInit {
  planes: PlanEstudio[] = [];
  semestres: number[] = [];
  cursos: Curso[] = [];
  periodos: PeriodoAcademico[] = [];
  programacion: ProgramacionHorario[] = [];
  resumen?: ResumenSemestre;
  cursoDetalle?: CursoDetalle;
  selectedPlan?: number;
  selectedSemester?: number;
  selectedPeriodo?: string;
  buscar = '';
  cargando = false;
  cargandoSemestres = false;
  error = '';

  constructor(private apiService: ApiService, private route: ActivatedRoute) {}

  ngOnInit(): void {
    this.route.fragment.subscribe(fragment => {
      if (fragment) setTimeout(() => this.desplazarA(fragment));
    });
    this.apiService.getPeriodos().subscribe(data => {
      this.periodos = data;
      this.selectedPeriodo = data.find(p => p.activo)?.cod_periodo ?? data[0]?.cod_periodo;
    });
    this.apiService.getPlanes().subscribe({
      next: data => {
        this.planes = data;
        this.selectedPlan = data.find(plan => plan.vigente)?.corr_pe ?? data[0]?.corr_pe;
        this.seleccionarPlan();
      },
      error: () => this.error = 'No se pudo conectar con la API.'
    });
  }

  private desplazarA(fragmento: string): void {
    document.getElementById(fragmento)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  get planSeleccionado(): PlanEstudio | undefined {
    return this.planes.find(plan => plan.corr_pe === Number(this.selectedPlan));
  }

  seleccionarPlan(): void {
    this.selectedSemester = undefined;
    this.buscar = '';
    this.semestres = [];
    this.limpiarResultados();
    if (!this.selectedPlan) return;
    this.cargandoSemestres = true;
    this.apiService.getSemestres(Number(this.selectedPlan)).subscribe({
      next: data => {
        this.semestres = data;
        this.cargandoSemestres = false;
      },
      error: () => {
        this.error = 'No se pudieron cargar los semestres de la malla.';
        this.cargandoSemestres = false;
      }
    });
  }

  seleccionarSemestre(): void {
    this.buscar = '';
    this.limpiarResultados();
    if (this.selectedSemester) this.consultar();
  }

  consultar(): void {
    if (!this.selectedPlan || !this.selectedSemester) return;
    const plan = Number(this.selectedPlan);
    const semestre = Number(this.selectedSemester);
    this.cargando = true;
    this.error = '';
    this.cursoDetalle = undefined;
    this.apiService.getCursos(plan, semestre, this.buscar).subscribe({
      next: data => { this.cursos = data; this.cargando = false; },
      error: () => { this.error = 'No se pudieron cargar los cursos.'; this.cargando = false; }
    });
    this.apiService.getResumenSemestre(plan, semestre).subscribe({
      next: data => this.resumen = data,
      error: () => this.resumen = undefined
    });
    this.cargarProgramacion();
  }

  cargarProgramacion(): void {
    if (!this.selectedPlan || !this.selectedSemester) {
      this.programacion = [];
      return;
    }
    this.apiService.getProgramacion(
      Number(this.selectedPlan), Number(this.selectedSemester), this.selectedPeriodo
    ).subscribe({
      next: data => this.programacion = data,
      error: () => this.programacion = []
    });
  }

  verDetalle(curso: Curso): void {
    if (!this.selectedPlan) return;
    this.apiService.getCursoDetalle(Number(this.selectedPlan), curso.cod_curso).subscribe({
      next: data => this.cursoDetalle = data,
      error: () => this.error = 'No se pudo cargar el detalle del curso.'
    });
  }

  cerrarDetalle(): void {
    this.cursoDetalle = undefined;
  }

  limpiarFiltros(): void {
    this.buscar = '';
    this.cursoDetalle = undefined;
    if (this.selectedSemester) this.consultar();
  }

  private limpiarResultados(): void {
    this.cursos = [];
    this.programacion = [];
    this.resumen = undefined;
    this.cursoDetalle = undefined;
    this.error = '';
  }

  semestreRomano(numero: number): string {
    return ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'][numero - 1];
  }

  tipoSesion(tipo: string): string {
    return tipo === 'T' ? 'Teoría' : 'Práctica';
  }

  hora(valor: string): string {
    return valor?.slice(0, 5);
  }
}
