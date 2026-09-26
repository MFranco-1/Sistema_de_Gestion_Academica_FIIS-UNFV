import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';

import { ApiService, Docente, DocentePayload } from '../../services/api.service';

@Component({
  selector: 'app-docentes',
  templateUrl: './docentes.component.html',
  styleUrls: ['./docentes.component.css']
})
export class DocentesComponent implements OnInit {
  docentes: Docente[] = [];
  buscar = '';
  categoria = '';
  cargando = false;
  guardando = false;
  mostrarFormulario = false;
  codigoEdicion = '';
  codigo = '';
  formulario: DocentePayload = this.formularioVacio();
  mensaje = '';
  error = '';

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.consultar();
  }

  consultar(): void {
    this.cargando = true;
    this.error = '';
    this.apiService.getDocentes(this.buscar, this.categoria).subscribe({
      next: data => {
        this.docentes = data;
        this.cargando = false;
      },
      error: () => {
        this.error = 'No se pudo cargar la plana docente.';
        this.cargando = false;
      }
    });
  }

  limpiarFiltros(): void {
    this.buscar = '';
    this.categoria = '';
    this.consultar();
  }

  nuevo(): void {
    this.codigoEdicion = '';
    this.codigo = '';
    this.formulario = this.formularioVacio();
    this.mostrarFormulario = true;
    this.mensaje = '';
    this.error = '';
  }

  editar(docente: Docente): void {
    this.codigoEdicion = docente.cod_docente;
    this.codigo = docente.cod_docente;
    this.formulario = {
      apellidos_nombres: docente.apellidos_nombres,
      categoria: docente.categoria,
      dedicacion: docente.dedicacion,
      departamento: docente.departamento,
      fuente: docente.fuente
    };
    this.mostrarFormulario = true;
    this.mensaje = '';
    this.error = '';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  cancelar(): void {
    this.mostrarFormulario = false;
    this.codigoEdicion = '';
  }

  guardar(): void {
    this.guardando = true;
    this.mensaje = '';
    this.error = '';
    const solicitud = this.codigoEdicion
      ? this.apiService.editarDocente(this.codigoEdicion, this.formulario)
      : this.apiService.crearDocente({ ...this.formulario, cod_docente: this.codigo });
    solicitud.subscribe({
      next: docente => {
        this.guardando = false;
        this.mostrarFormulario = false;
        this.codigoEdicion = '';
        this.mensaje = `Docente ${docente.apellidos_nombres} guardado correctamente.`;
        this.consultar();
      },
      error: error => {
        this.guardando = false;
        this.mostrarError(error);
      }
    });
  }

  eliminar(docente: Docente): void {
    if (!confirm(`¿Eliminar al docente ${docente.apellidos_nombres}?`)) return;
    this.mensaje = '';
    this.error = '';
    this.apiService.eliminarDocente(docente.cod_docente).subscribe({
      next: respuesta => {
        this.mensaje = respuesta.mensaje;
        this.consultar();
      },
      error: error => this.mostrarError(error)
    });
  }

  private formularioVacio(): DocentePayload {
    return {
      apellidos_nombres: '', categoria: 'CONTRATADO', dedicacion: 'TIEMPO PARCIAL',
      departamento: 'Ingeniería de Sistemas', fuente: 'Registro institucional FIIS-UNFV'
    };
  }

  private mostrarError(error: HttpErrorResponse): void {
    const detalle = error.error?.detail;
    this.error = typeof detalle === 'string' ? detalle : 'No se pudo completar la operación.';
  }
}
