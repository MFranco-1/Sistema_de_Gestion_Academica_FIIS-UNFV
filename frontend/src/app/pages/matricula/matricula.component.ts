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

  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit(): void {
    this.api.getPeriodos().subscribe(data => {
      this.periodos = data;
      this.periodoSeleccionado = data.find(p => p.activo)?.cod_periodo ?? data[0]?.cod_periodo ?? '';
      this.cargarFicha();
    });
  }

  cargarFicha(): void {
    this.api.getMiEstudiante().subscribe({
      next: estudiante => { this.estudiante = estudiante; this.cargando = false; this.cargarOfertas(); this.cargarHistorial(); },
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
      next: () => { this.mensaje = 'Matrícula registrada correctamente.'; this.cargarOfertas(); this.cargarHistorial(); },
      error: error => this.mostrarError(error)
    });
  }

  semestreRomano(numero: number): string { return ['I','II','III','IV','V','VI','VII','VIII','IX','X'][numero - 1]; }
  private mostrarError(error: HttpErrorResponse): void { this.mensaje = ''; this.error = error.error?.detail || 'No se pudo completar la operación.'; }
}
