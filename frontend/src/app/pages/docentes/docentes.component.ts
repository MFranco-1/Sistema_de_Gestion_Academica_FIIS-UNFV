import { Component, OnInit } from '@angular/core';

import { ApiService, Docente } from '../../services/api.service';

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
}
