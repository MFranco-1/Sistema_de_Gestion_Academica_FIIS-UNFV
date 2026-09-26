import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ApiService, Estudiante, MatriculaDetalle, MatriculaResumen, OfertaCurso, PeriodoAcademico } from '../../services/api.service';

@Component({ selector: 'app-gestion-matriculas', templateUrl: './gestion-matriculas.component.html', styleUrls: ['./gestion-matriculas.component.css'] })
export class GestionMatriculasComponent implements OnInit {
  estudiantes: Estudiante[] = [];
  periodos: PeriodoAcademico[] = [];
  estudiante?: Estudiante;
  codigo = '';
  periodo = '';
  ofertas: OfertaCurso[] = [];
  matriculas: MatriculaResumen[] = [];
  seleccionadas = new Set<number>();
  mensaje = '';
  error = '';
  constructor(private api: ApiService) {}
  ngOnInit(): void {
    this.api.getEstudiantes().subscribe({ next: data => this.estudiantes = data, error: e => this.mostrarError(e) });
    this.api.getPeriodos().subscribe({
      next: data => { this.periodos = data; this.periodo = data.find(p => p.activo)?.cod_periodo || data[0]?.cod_periodo || ''; },
      error: e => this.mostrarError(e)
    });
  }
  seleccionar(): void {
    this.codigo = this.codigo.trim();
    this.estudiante = this.estudiantes.find(e => e.cod_estudiante === this.codigo);
    this.ofertas = []; this.matriculas = []; this.seleccionadas.clear();
    if (this.estudiante) {
      this.error = '';
      this.cargarOfertas(); this.cargarHistorial();
    } else {
      this.error = this.codigo ? 'No se encontró un estudiante con ese código.' : 'Ingrese un código de estudiante.';
    }
  }
  cargarOfertas(): void {
    if (!this.estudiante || !this.periodo) return;
    this.seleccionadas.clear();
    this.api.getOfertasEstudiante(this.estudiante.cod_estudiante, this.periodo).subscribe({ next: data => this.ofertas = data, error: e => this.mostrarError(e) });
  }
  cargarHistorial(): void {
    if (!this.estudiante) return;
    this.api.getMatriculasEstudiante(this.estudiante.cod_estudiante).subscribe({ next: data => this.matriculas = data, error: e => this.mostrarError(e) });
  }
  alternar(id: number, value: boolean): void { value ? this.seleccionadas.add(id) : this.seleccionadas.delete(id); }
  matricular(): void {
    if (!this.estudiante || !this.seleccionadas.size) return;
    this.api.crearMatricula(this.estudiante.cod_estudiante, this.periodo, [...this.seleccionadas]).subscribe({ next: () => { this.mensaje = 'Matrícula registrada correctamente.'; this.cargarOfertas(); this.cargarHistorial(); }, error: e => this.mostrarError(e) });
  }
  guardarResultado(detalle: MatriculaDetalle): void {
    this.api.registrarResultado(detalle.id_matricula, detalle.id_oferta, detalle).subscribe({ next: data => { this.mensaje = data.mensaje; this.cargarHistorial(); }, error: e => this.mostrarError(e) });
  }
  actualizarResultado(detalle: MatriculaDetalle): void {
    if (detalle.resultado === 'RETIRADO') return;
    const notas = [detalle.nota_practicas, detalle.nota_parcial, detalle.nota_examen_final];
    if (notas.some(nota => nota === null || nota === undefined || nota < 0 || nota > 20)) {
      detalle.nota_final = undefined;
      detalle.resultado = 'MATRICULADO';
      return;
    }
    detalle.nota_final = Math.round(Number(detalle.nota_practicas) * .40 + Number(detalle.nota_parcial) * .30 + Number(detalle.nota_examen_final) * .30);
    detalle.resultado = detalle.nota_final >= 11 ? 'APROBADO' : 'DESAPROBADO';
  }
  alternarRetiro(detalle: MatriculaDetalle): void {
    if (detalle.resultado === 'RETIRADO') {
      detalle.resultado = 'MATRICULADO';
    } else {
      detalle.resultado = 'RETIRADO';
      detalle.nota_practicas = undefined;
      detalle.nota_parcial = undefined;
      detalle.nota_examen_final = undefined;
      detalle.nota_final = undefined;
    }
  }
  guardarTodos(matricula: MatriculaResumen): void {
    this.mensaje = ''; this.error = '';
    this.api.registrarResultadosLote(matricula.id_matricula, matricula.detalles).subscribe({
      next: data => { this.mensaje = data.mensaje; this.cargarHistorial(); },
      error: e => this.mostrarError(e)
    });
  }
  romano(n: number): string { return ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'][n - 1]; }
  private mostrarError(error: HttpErrorResponse): void {
    this.mensaje = '';
    const detalle = error.error?.detail;
    this.error = typeof detalle === 'string'
      ? detalle
      : Array.isArray(detalle)
        ? detalle.map(item => item?.msg || 'Dato inválido').join(' ')
        : 'No se pudo completar la operación.';
  }
}
