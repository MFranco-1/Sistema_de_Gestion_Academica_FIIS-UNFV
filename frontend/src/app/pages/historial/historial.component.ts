import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ApiService, Estudiante, MatriculaResumen } from '../../services/api.service';

@Component({ selector: 'app-historial', templateUrl: './historial.component.html', styleUrls: ['../matricula/matricula.component.css'] })
export class HistorialComponent implements OnInit {
  estudiante?: Estudiante;
  matriculas: MatriculaResumen[] = [];
  error = '';
  constructor(private api: ApiService) {}
  ngOnInit(): void {
    this.api.getMiEstudiante().subscribe({
      next: estudiante => {
        this.estudiante = estudiante;
        this.api.getMatriculasEstudiante(estudiante.cod_estudiante).subscribe({
          next: data => this.matriculas = data,
          error: e => this.mostrarError(e)
        });
      },
      error: e => this.mostrarError(e)
    });
  }
  romano(n: number): string { return ['I','II','III','IV','V','VI','VII','VIII','IX','X'][n - 1]; }
  private mostrarError(error: HttpErrorResponse): void { this.error = typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo cargar el historial.'; }
}
