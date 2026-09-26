import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ApiService, PerfilAdministracion } from '../../services/api.service';

interface PermisoOpcion { codigo: string; nombre: string; descripcion: string; }

@Component({ selector: 'app-perfiles', templateUrl: './perfiles.component.html', styleUrls: ['./perfiles.component.css'] })
export class PerfilesComponent implements OnInit {
  readonly permisosDisponibles: PermisoOpcion[] = [
    { codigo: 'GESTION_CURRICULAR', nombre: 'Gestión curricular', descripcion: 'Consultar planes, cursos, prerrequisitos y programación.' },
    { codigo: 'PLANA_DOCENTE', nombre: 'Plana docente', descripcion: 'Consultar la información de docentes.' },
    { codigo: 'MANTENIMIENTO_ACADEMICO', nombre: 'Mantenimiento académico', descripcion: 'Crear y editar cursos, prerrequisitos y horarios.' },
    { codigo: 'GESTION_ESTUDIANTES', nombre: 'Gestión de estudiantes', descripcion: 'Registrar, editar y retirar estudiantes.' },
    { codigo: 'GESTION_USUARIOS', nombre: 'Gestión de usuarios', descripcion: 'Administrar cuentas y asignar perfiles.' },
    { codigo: 'GESTION_PERFILES', nombre: 'Gestión de perfiles', descripcion: 'Crear perfiles y configurar sus permisos.' },
    { codigo: 'MATRICULA_PROPIA', nombre: 'Matrícula personal', descripcion: 'Matricularse y consultar el historial propio.' },
    { codigo: 'GESTION_MATRICULAS', nombre: 'Gestión de matrículas', descripcion: 'Matricular estudiantes y administrar sus resultados.' },
  ];
  perfiles: PerfilAdministracion[] = [];
  editando?: PerfilAdministracion;
  creando = false;
  codigo = '';
  nombre = '';
  permisos = new Set<string>();
  mensaje = '';
  error = '';
  constructor(private api: ApiService) {}
  ngOnInit(): void { this.cargar(); }
  cargar(): void { this.api.getPerfiles().subscribe({ next: data => this.perfiles = data, error: e => this.mostrarError(e) }); }
  nuevo(): void { this.cancelar(); this.creando = true; }
  editar(perfil: PerfilAdministracion): void { this.cancelar(); this.editando = perfil; this.nombre = perfil.nombre; this.codigo = perfil.codigo; this.permisos = new Set(perfil.permisos); }
  alternarPermiso(codigo: string, activo: boolean): void { activo ? this.permisos.add(codigo) : this.permisos.delete(codigo); }
  guardar(): void {
    this.mensaje = '';
    this.error = '';
    if (!this.permisos.size) {
      this.error = 'Seleccione al menos un permiso para que el perfil pueda ingresar al sistema.';
      return;
    }
    const request = this.creando
      ? this.api.crearPerfil(this.codigo.trim().toUpperCase(), this.nombre, [...this.permisos])
      : this.api.editarPerfil(this.editando!.id_perfil, this.nombre, [...this.permisos]);
    request.subscribe({ next: () => { this.mensaje = 'Perfil guardado correctamente. Los usuarios deben cambiar de perfil o iniciar sesión nuevamente para aplicar los permisos.'; this.cancelar(); this.cargar(); }, error: e => this.mostrarError(e) });
  }
  eliminar(perfil: PerfilAdministracion): void {
    if (!confirm(`¿Eliminar el perfil ${perfil.nombre}?`)) return;
    this.api.eliminarPerfil(perfil.id_perfil).subscribe({ next: data => { this.mensaje = data.mensaje; this.cargar(); }, error: e => this.mostrarError(e) });
  }
  cancelar(): void { this.editando = undefined; this.creando = false; this.codigo = ''; this.nombre = ''; this.permisos = new Set<string>(); }
  nombrePermiso(codigo: string): string { return this.permisosDisponibles.find(p => p.codigo === codigo)?.nombre || codigo; }
  icono(perfil: PerfilAdministracion): string { return perfil.codigo === 'ADMINISTRADOR' ? 'admin_panel_settings' : perfil.codigo === 'ESTUDIANTE' ? 'school' : 'badge'; }
  private mostrarError(error: HttpErrorResponse): void { this.mensaje = ''; this.error = error.error?.detail || 'No se pudo completar la operación.'; }
}
