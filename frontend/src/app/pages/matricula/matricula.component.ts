import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ApiService, Estudiante, MatriculaResumen, OfertaCurso, PeriodoAcademico } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({ selector: 'app-matricula', templateUrl: './matricula.component.html', styleUrls: ['./matricula.component.css'] })
export class MatriculaComponent implements OnInit {
  estudiante?: Estudiante;
  periodos: PeriodoAcademico[] = [];
  ofertas: OfertaCurso[] = [];
  matriculas: MatriculaResumen[] = [];
  seleccionadas = new Set<number>();
  periodoSeleccionado = '';
  mensaje = '';
  error = '';
  cargando = true;
  fotoPerfil = '';

  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit(): void {
    this.cargarFicha();
    this.api.getPeriodos().subscribe({
      next: data => {
        this.periodos = data;
        this.periodoSeleccionado = data.find(p => p.activo)?.cod_periodo ?? data[0]?.cod_periodo ?? '';
        this.cargarOfertas();
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
        this.cargarOfertas();
      },
      error: error => { this.cargando = false; this.mostrarError(error); }
    });
  }

  cargarOfertas(): void {
    if (!this.estudiante || !this.periodoSeleccionado) return;
    this.seleccionadas.clear();
    this.api.getOfertasEstudiante(this.estudiante.cod_estudiante, this.periodoSeleccionado).subscribe({
      next: data => this.ofertas = data,
      error: error => this.mostrarError(error)
    });
  }

  cargarHistorial(): void {
    if (!this.estudiante) return;
    this.api.getMatriculasEstudiante(this.estudiante.cod_estudiante).subscribe({
      next: data => this.matriculas = data,
      error: error => this.mostrarError(error)
    });
  }

  alternarOferta(id: number, seleccionada: boolean): void {
    seleccionada ? this.seleccionadas.add(id) : this.seleccionadas.delete(id);
  }

  registrarMatricula(): void {
    if (!this.estudiante || !this.seleccionadas.size) return;
    this.mensaje = ''; this.error = '';
    this.api.crearMatricula(this.estudiante.cod_estudiante, this.periodoSeleccionado, [...this.seleccionadas]).subscribe({
      next: () => { this.mensaje = 'Matrícula registrada correctamente.'; this.cargarFicha(); },
      error: error => this.mostrarError(error)
    });
  }

  semestreRomano(numero: number): string { return ['I','II','III','IV','V','VI','VII','VIII','IX','X'][numero - 1]; }
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
    return this.ofertas.filter(item => this.seleccionadas.has(item.id_oferta)).reduce((total, item) => total + item.cred, 0);
  }
  private mostrarError(error: HttpErrorResponse): void {
    this.mensaje = '';
    const detalle = error.error?.detail;
    this.error = typeof detalle === 'string' ? detalle : 'No se pudo completar la operación.';
  }
}
