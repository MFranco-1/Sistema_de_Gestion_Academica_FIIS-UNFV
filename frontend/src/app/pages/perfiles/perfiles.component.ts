import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ApiService, PerfilAdministracion } from '../../services/api.service';

@Component({ selector: 'app-perfiles', templateUrl: './perfiles.component.html', styleUrls: ['./perfiles.component.css'] })
export class PerfilesComponent implements OnInit {
  perfiles: PerfilAdministracion[] = [];
  editando?: PerfilAdministracion;
  nombre = '';
  mensaje = '';
  error = '';
  constructor(private api: ApiService) {}
  ngOnInit(): void { this.cargar(); }
  cargar(): void { this.api.getPerfiles().subscribe({ next: data => this.perfiles = data, error: e => this.mostrarError(e) }); }
  editar(perfil: PerfilAdministracion): void { this.editando = perfil; this.nombre = perfil.nombre; this.mensaje = ''; this.error = ''; }
  guardar(): void {
    if (!this.editando) return;
    this.api.editarPerfil(this.editando.id_perfil, this.nombre).subscribe({ next: () => { this.mensaje = 'Perfil actualizado correctamente.'; this.cancelar(); this.cargar(); }, error: e => this.mostrarError(e) });
  }
  cancelar(): void { this.editando = undefined; this.nombre = ''; }
  descripcion(codigo: string): string { return codigo === 'ADMINISTRADOR' ? 'Acceso a gestión curricular, estudiantes, usuarios, perfiles y mantenimiento académico.' : 'Acceso personal a matrícula, cursos disponibles e historial académico.'; }
  private mostrarError(error: HttpErrorResponse): void { this.mensaje = ''; this.error = error.error?.detail || 'No se pudo completar la operación.'; }
}
