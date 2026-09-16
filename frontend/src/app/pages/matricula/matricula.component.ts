import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ApiService, Estudiante, EstudiantePayload, MatriculaDetalle, MatriculaResumen,
  OfertaCurso, PeriodoAcademico, PlanEstudio
} from '../../services/api.service';

@Component({
  selector: 'app-matricula',
  templateUrl: './matricula.component.html',
  styleUrls: ['./matricula.component.css']
})
export class MatriculaComponent implements OnInit {
  planes: PlanEstudio[] = [];
  periodos: PeriodoAcademico[] = [];
  estudiantes: Estudiante[] = [];
  estudianteSeleccionado?: Estudiante;
  ofertas: OfertaCurso[] = [];
  matriculas: MatriculaResumen[] = [];
  ofertasSeleccionadas = new Set<number>();
  periodoSeleccionado = '';
  editandoCodigo = '';
  mensaje = '';
  error = '';
  formulario: EstudiantePayload = this.nuevoEstudiante();

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getPlanes().subscribe(data => this.planes = data);
    this.api.getPeriodos().subscribe(data => {
      this.periodos = data;
      this.periodoSeleccionado = data.find(p => p.activo)?.cod_periodo ?? data[0]?.cod_periodo ?? '';
    });
    this.cargarEstudiantes();
  }

  cargarEstudiantes(): void {
    this.api.getEstudiantes().subscribe({
      next: data => this.estudiantes = data,
      error: error => this.mostrarError(error)
    });
  }

  guardarEstudiante(): void {
    this.limpiarMensajes();
    const datos = { ...this.formulario };
    const operacion = this.editandoCodigo
      ? this.api.editarEstudiante(this.editandoCodigo, datos)
      : this.api.crearEstudiante(datos);
    operacion.subscribe({
      next: estudiante => {
        this.mensaje = this.editandoCodigo ? 'Estudiante actualizado correctamente.' : 'Estudiante registrado correctamente.';
        this.cancelarEdicion();
        this.cargarEstudiantes();
        this.seleccionarEstudiante(estudiante);
      },
      error: error => this.mostrarError(error)
    });
  }

  editarEstudiante(estudiante: Estudiante): void {
    this.editandoCodigo = estudiante.cod_estudiante;
    this.formulario = {
      cod_estudiante: estudiante.cod_estudiante, dni: estudiante.dni,
      apellidos_nombres: estudiante.apellidos_nombres, correo: estudiante.correo,
      cod_fac: estudiante.cod_fac, cod_esc: estudiante.cod_esc,
      corr_pe: estudiante.corr_pe, ciclo_actual: estudiante.ciclo_actual,
      estado: estudiante.estado
    };
    this.limpiarMensajes();
  }

  eliminarEstudiante(estudiante: Estudiante): void {
    if (!confirm(`¿Eliminar al estudiante ${estudiante.cod_estudiante}?`)) return;
    this.api.eliminarEstudiante(estudiante.cod_estudiante).subscribe({
      next: data => {
        this.mensaje = data.mensaje;
        if (this.estudianteSeleccionado?.cod_estudiante === estudiante.cod_estudiante) {
          this.estudianteSeleccionado = undefined;
          this.ofertas = [];
          this.matriculas = [];
        }
        this.cargarEstudiantes();
      },
      error: error => this.mostrarError(error)
    });
  }

  cancelarEdicion(): void {
    this.editandoCodigo = '';
    this.formulario = this.nuevoEstudiante();
  }

  seleccionarEstudiante(estudiante: Estudiante): void {
    this.estudianteSeleccionado = estudiante;
    this.ofertasSeleccionadas.clear();
    this.cargarOfertas();
    this.cargarHistorial();
  }

  cargarOfertas(): void {
    if (!this.estudianteSeleccionado || !this.periodoSeleccionado) return;
    this.ofertasSeleccionadas.clear();
    this.api.getOfertasEstudiante(
      this.estudianteSeleccionado.cod_estudiante, this.periodoSeleccionado
    ).subscribe({
      next: data => this.ofertas = data,
      error: error => this.mostrarError(error)
    });
  }

  alternarOferta(idOferta: number, seleccionado: boolean): void {
    seleccionado ? this.ofertasSeleccionadas.add(idOferta) : this.ofertasSeleccionadas.delete(idOferta);
  }

  registrarMatricula(): void {
    if (!this.estudianteSeleccionado || !this.ofertasSeleccionadas.size) {
      this.error = 'Seleccione al menos un curso disponible.';
      return;
    }
    this.limpiarMensajes();
    this.api.crearMatricula(
      this.estudianteSeleccionado.cod_estudiante,
      this.periodoSeleccionado,
      Array.from(this.ofertasSeleccionadas)
    ).subscribe({
      next: () => {
        this.mensaje = 'Matrícula registrada correctamente.';
        this.cargarOfertas();
        this.cargarHistorial();
      },
      error: error => this.mostrarError(error)
    });
  }

  cargarHistorial(): void {
    if (!this.estudianteSeleccionado) return;
    this.api.getMatriculasEstudiante(this.estudianteSeleccionado.cod_estudiante).subscribe({
      next: data => this.matriculas = data,
      error: error => this.mostrarError(error)
    });
  }

  guardarResultado(detalle: MatriculaDetalle): void {
    const nota = detalle.nota_final === null || detalle.nota_final === undefined
      ? undefined : Number(detalle.nota_final);
    this.api.registrarResultado(
      detalle.id_matricula, detalle.id_oferta, nota, detalle.resultado
    ).subscribe({
      next: data => {
        this.mensaje = data.mensaje;
        this.cargarHistorial();
        this.cargarOfertas();
      },
      error: error => this.mostrarError(error)
    });
  }

  semestreRomano(numero: number): string {
    return ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'][numero - 1];
  }

  private nuevoEstudiante(): EstudiantePayload {
    return {
      cod_estudiante: '', dni: '', apellidos_nombres: '', correo: '',
      cod_fac: 1, cod_esc: 1, corr_pe: 2, ciclo_actual: 1, estado: 'ACTIVO'
    };
  }

  private limpiarMensajes(): void { this.mensaje = ''; this.error = ''; }

  private mostrarError(error: HttpErrorResponse): void {
    this.mensaje = '';
    const detalle = error.error?.detail;
    this.error = typeof detalle === 'string' ? detalle : 'No se pudo completar la operación.';
  }
}
