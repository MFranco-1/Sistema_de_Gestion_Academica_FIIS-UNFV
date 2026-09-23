import { Component, OnInit } from '@angular/core';
import { ApiService, Curso, Estudiante } from '../../services/api.service';

@Component({ selector: 'app-mi-malla', templateUrl: './mi-malla.component.html', styleUrls: ['./mi-malla.component.css'] })
export class MiMallaComponent implements OnInit {
  estudiante?: Estudiante;
  cursos: Curso[] = [];
  error = '';
  constructor(private api: ApiService) {}
  ngOnInit(): void {
    this.api.getMiEstudiante().subscribe({
      next: estudiante => {
        this.estudiante = estudiante;
        this.api.getCursos(estudiante.corr_pe).subscribe({ next: data => this.cursos = data, error: () => this.error = 'No se pudo cargar la malla.' });
      },
      error: () => this.error = 'No se pudo cargar la ficha del estudiante.'
    });
  }
  romano(n: number): string { return ['I','II','III','IV','V','VI','VII','VIII','IX','X'][n - 1]; }
}
