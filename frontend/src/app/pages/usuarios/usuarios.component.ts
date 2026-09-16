import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ApiService, Estudiante, PerfilAdministracion, UsuarioAdministracion, UsuarioPayload } from '../../services/api.service';

@Component({ selector: 'app-usuarios', templateUrl: './usuarios.component.html', styleUrls: ['./usuarios.component.css'] })
export class UsuariosComponent implements OnInit {
  usuarios: UsuarioAdministracion[] = [];
  estudiantes: Estudiante[] = [];
  perfilesDisponibles: PerfilAdministracion[] = [];
  filtro = '';
  formularioVisible = false;
  editandoId?: number;
  perfilesSeleccionados = new Set<string>(['ESTUDIANTE']);
  mensaje = '';
  error = '';
  form: UsuarioPayload = this.nuevoUsuario();

  constructor(private api: ApiService) {}
  ngOnInit(): void { this.cargar(); this.api.getEstudiantes().subscribe(data => this.estudiantes = data); this.api.getPerfiles().subscribe(data => this.perfilesDisponibles = data); }

  get filtrados(): UsuarioAdministracion[] {
    const term = this.filtro.trim().toLowerCase();
    return !term ? this.usuarios : this.usuarios.filter(u => [u.nombre_usuario, u.nombre_mostrar, u.cod_estudiante || '', ...u.perfiles].some(v => v.toLowerCase().includes(term)));
  }

  cargar(): void { this.api.getUsuarios().subscribe({ next: data => this.usuarios = data, error: e => this.mostrarError(e) }); }
  nuevo(): void { this.cancelar(); this.formularioVisible = true; }
  editar(usuario: UsuarioAdministracion): void {
    this.editandoId = usuario.id_usuario; this.formularioVisible = true;
    this.form = { nombre_mostrar: usuario.nombre_mostrar, cod_estudiante: usuario.cod_estudiante, perfiles: [...usuario.perfiles], activo: usuario.activo, clave: '' };
    this.perfilesSeleccionados = new Set(usuario.perfiles);
  }
  alternarPerfil(codigo: string, activo: boolean): void { activo ? this.perfilesSeleccionados.add(codigo) : this.perfilesSeleccionados.delete(codigo); }
  nombrePerfil(codigo: string): string { return this.perfilesDisponibles.find(p => p.codigo === codigo)?.nombre || codigo; }
  guardar(): void {
    this.mensaje = ''; this.error = '';
    const perfiles = [...this.perfilesSeleccionados];
    if (!perfiles.length) { this.error = 'Seleccione al menos un perfil.'; return; }
    const datos = { ...this.form, perfiles, cod_estudiante: this.form.cod_estudiante || undefined };
    const request = this.editandoId ? this.api.editarUsuario(this.editandoId, datos) : this.api.crearUsuario(datos);
    request.subscribe({ next: () => { this.mensaje = 'Usuario guardado correctamente.'; this.cancelar(); this.cargar(); }, error: e => this.mostrarError(e) });
  }
  alternarEstado(usuario: UsuarioAdministracion): void {
    this.api.editarUsuario(usuario.id_usuario, { nombre_mostrar: usuario.nombre_mostrar, cod_estudiante: usuario.cod_estudiante, perfiles: usuario.perfiles, activo: !usuario.activo }).subscribe({ next: () => { this.mensaje = usuario.activo ? 'Usuario desactivado.' : 'Usuario activado.'; this.cargar(); }, error: e => this.mostrarError(e) });
  }
  eliminar(usuario: UsuarioAdministracion): void {
    if (!confirm(`¿Eliminar al usuario ${usuario.nombre_usuario}?`)) return;
    this.api.eliminarUsuario(usuario.id_usuario).subscribe({ next: data => { this.mensaje = data.mensaje; this.cargar(); }, error: e => this.mostrarError(e) });
  }
  cancelar(): void { this.formularioVisible = false; this.editandoId = undefined; this.form = this.nuevoUsuario(); this.perfilesSeleccionados = new Set(['ESTUDIANTE']); }
  private nuevoUsuario(): UsuarioPayload { return { nombre_usuario: '', clave: '', nombre_mostrar: '', perfiles: ['ESTUDIANTE'], activo: true }; }
  private mostrarError(error: HttpErrorResponse): void { this.mensaje = ''; this.error = error.error?.detail || 'No se pudo completar la operación.'; }
}
